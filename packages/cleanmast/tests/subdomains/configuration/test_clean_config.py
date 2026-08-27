"""Tests for the clean pipeline configuration models and discovery.

Mirrors the Julia source of truth (CleanRules.jl, ProcessCleanConfig.jl,
RecommendTowerShadingCommand.jl) — parsing only; Python never authors
these files.
"""

from pathlib import Path

import pytest
import tomli_w
from cleanmast.subdomains.configuration import (
    CleanRule,
    CleanRulesFile,
    ProcessCleanConfiguration,
    ProcessCleanMast,
    ProjectConfig,
    TowerShadingConfiguration,
    load_clean_rules,
    load_config,
)
from pydantic import ValidationError


def _rule(**overrides):
    base = {
        "name": "Wind Speed Range",
        "sensorType": "WindSpeed",
        "out_of_range": {"min": 0.0, "max": 30.0},
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


class TestCleanRuleParsing:
    """CleanRule parses all four criteria blocks exactly like Julia from_dict."""

    def test_out_of_range(self):
        rule = CleanRule.model_validate(_rule())
        assert rule.name == "Wind Speed Range"
        assert rule.sensorType == "WindSpeed"
        assert rule.height.min is None and rule.height.max is None
        assert rule.out_of_range is not None
        assert rule.out_of_range.min == 0.0
        assert rule.out_of_range.max == 30.0

    def test_layer_difference_with_height_filter_and_empty_ranges(self):
        rule = CleanRule.model_validate(_rule(
            name="High Wind Speed Layer Difference",
            out_of_range=None,
            height={"min": 70.0},
            layer_difference={
                "lower_layer_height": 20.0,
                "abs_diff": {"max": 2.0},
                "lower_wind_speed": {},
            },
        ))
        assert rule.height.min == 70.0
        assert rule.layer_difference is not None
        assert rule.layer_difference.lower_layer_height == 20.0
        # Empty TOML table parses as unbounded RangeCriteria (Julia get(..., nothing))
        assert rule.layer_difference.abs_diff.min is None
        assert rule.layer_difference.abs_diff.max == 2.0
        assert rule.layer_difference.lower_wind_speed.min is None
        assert rule.layer_difference.lower_wind_speed.max is None

    def test_icing(self):
        rule = CleanRule.model_validate(_rule(
            name="Icing WS Detection",
            out_of_range=None,
            icing={"time_range": 18000, "max_change": 0.02},
        ))
        assert rule.icing is not None
        assert rule.icing.time_range == 18000
        assert rule.icing.max_change == 0.02

    def test_availability(self):
        rule = CleanRule.model_validate(_rule(
            name="Lidar Availability Check",
            sensorType="DataAvailability",
            out_of_range=None,
            availability={"low_threshold": 80.0},
        ))
        assert rule.availability is not None
        assert rule.availability.low_threshold == 80.0

    def test_exactly_one_criteria_enforced(self):
        with pytest.raises(ValidationError, match="exactly one"):
            CleanRule.model_validate(_rule(out_of_range=None))
        with pytest.raises(ValidationError, match="exactly one"):
            CleanRule.model_validate(_rule(
                icing={"time_range": 1, "max_change": 0.1},
            ))

    def test_preset_files_parse(self):
        presets = (
            Path(__file__).parents[3]
            / "src/cleanmast/scaffold/formats/clean"
        )
        files = sorted(presets.glob("*.toml"))
        assert len(files) == 4
        for path in files:
            rules = load_config(CleanRulesFile, path).rules
            assert rules, f"{path.name} parsed to no rules"


class TestProcessCleanConfiguration:
    """process-clean.toml parsing: rules as path string or inline list."""

    def _mast_dict(self, rules):
        return {
            "name": "M5057",
            "input": {"data": "./raw/M5057.parquet"},
            "output": {"data": "./clean/M5057.parquet"},
            "rules": rules,
        }

    def test_rules_as_path_string(self):
        config = ProcessCleanConfiguration.model_validate({
            "masts": [self._mast_dict("formats/clean/default.toml")],
        })
        mast = config.masts[0]
        assert isinstance(mast, ProcessCleanMast)
        assert mast.rules == "formats/clean/default.toml"

    def test_rules_as_inline_list(self):
        config = ProcessCleanConfiguration.model_validate({
            "masts": [self._mast_dict([_rule()])],
        })
        mast = config.masts[0]
        assert isinstance(mast.rules, list)
        assert isinstance(mast.rules[0], CleanRule)
        assert mast.rules[0].out_of_range.max == 30.0
        # Inline rules go through the same exactly-one validation
        with pytest.raises(ValidationError, match="exactly one"):
            ProcessCleanConfiguration.model_validate({
                "masts": [self._mast_dict([_rule(out_of_range=None)])],
            })

    def test_song_yuan_instance_parses(self):
        path = (
            Path(__file__).parents[5]
            / "test-data/cleanmast/song-yuan-tower-shading/process-clean.toml"
        )
        config = load_config(ProcessCleanConfiguration, path)
        assert [m.name for m in config.masts] == [
            "M1664", "M3142", "M5057", "M5972",
        ]


class TestLoadCleanRules:
    """load_clean_rules mirrors Julia load_rules path resolution."""

    def test_relative_path_resolved_against_project_dir(self, tmp_path):
        rules_file = {
            "rules": [
                _rule(),
                _rule(
                    name="Icing WD Detection",
                    sensorType="WindDirection",
                    out_of_range=None,
                    icing={"time_range": 18000, "max_change": 1},
                ),
            ]
        }
        (tmp_path / "formats" / "clean").mkdir(parents=True)
        with open(tmp_path / "formats/clean/default.toml", "wb") as f:
            tomli_w.dump(rules_file, f)

        rules = load_clean_rules("formats/clean/default.toml", tmp_path)
        assert [r.name for r in rules] == [
            "Wind Speed Range", "Icing WD Detection",
        ]

    def test_absolute_path_used_directly(self, tmp_path):
        rules_file = tmp_path / "standalone.toml"
        with open(rules_file, "wb") as f:
            tomli_w.dump({"rules": [_rule()]}, f)
        rules = load_clean_rules(str(rules_file), tmp_path)
        assert len(rules) == 1

    def test_inline_list_passthrough(self, tmp_path):
        inline = [CleanRule.model_validate(_rule())]
        assert load_clean_rules(inline, tmp_path) is inline

    def test_missing_rules_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_clean_rules("formats/clean/missing.toml", tmp_path)


class TestTowerShadingConfiguration:
    """tower-shading.toml as emitted by Julia RecommendTowerShadingCommand."""

    def _toml(self, tmp_path: Path) -> Path:
        path = tmp_path / "tower-shading.toml"
        with open(path, "wb") as f:
            tomli_w.dump({
                "masts": [
                    {
                        "name": "M5057",
                        "input": {"data": "./clean/M5057.parquet"},
                        "output": {"data": "./tower-shading/M5057.parquet"},
                    },
                ],
            }, f)
        return path

    def test_parses_julia_emitted_schema(self, tmp_path):
        config = load_config(TowerShadingConfiguration, self._toml(tmp_path))
        mast = config.masts[0]
        assert mast.name == "M5057"
        assert mast.input.data == "./clean/M5057.parquet"
        assert mast.output.data == "./tower-shading/M5057.parquet"
        # sensors key is stripped by Julia (strip_nothing_values)
        assert mast.input.sensors is None

    def test_song_yuan_expected_instance_parses(self):
        path = (
            Path(__file__).parents[5]
            / "test-data/cleanmast/song-yuan-tower-shading/expected/tower-shading.toml"
        )
        config = load_config(TowerShadingConfiguration, path)
        assert len(config.masts) == 4
        assert all(m.output.data.startswith("./tower-shading/") for m in config.masts)


class TestDiscoverCleanConfigs:
    """discover_process_clean_config / discover_tower_shading_config caching."""

    def _write_process_clean(self, tmp_path: Path) -> None:
        with open(tmp_path / "process-clean.toml", "wb") as f:
            tomli_w.dump({
                "masts": [
                    {
                        "name": "M1",
                        "input": {"data": "./raw/M1.parquet"},
                        "output": {"data": "./clean/M1.parquet"},
                        "rules": [_rule()],
                    },
                ],
            }, f)

    def _write_tower_shading(self, tmp_path: Path) -> None:
        with open(tmp_path / "tower-shading.toml", "wb") as f:
            tomli_w.dump({
                "masts": [
                    {
                        "name": "M1",
                        "input": {"data": "./clean/M1.parquet"},
                        "output": {"data": "./tower-shading/M1.parquet"},
                    },
                ],
            }, f)

    def test_missing_files_return_none(self, tmp_path):
        pc = ProjectConfig(tmp_path)
        assert pc.discover_process_clean_config() is None
        assert pc.discover_tower_shading_config() is None

    def test_discover_and_cache(self, tmp_path):
        self._write_process_clean(tmp_path)
        self._write_tower_shading(tmp_path)
        pc = ProjectConfig(tmp_path)

        first = pc.discover_process_clean_config()
        assert first is not None
        assert first.filename == "process-clean.toml"
        assert first.config.masts[0].name == "M1"
        # Cached: same object identity on the second call, file may even vanish
        assert pc.discover_process_clean_config() is first
        (tmp_path / "process-clean.toml").unlink()
        assert pc.discover_process_clean_config() is first

        first_ts = pc.discover_tower_shading_config()
        assert first_ts is not None
        assert first_ts.filename == "tower-shading.toml"
        assert pc.discover_tower_shading_config() is first_ts

    def test_registered_in_filenames(self):
        assert (
            ProjectConfig._FILENAMES[ProcessCleanConfiguration]
            == "process-clean.toml"
        )
        assert (
            ProjectConfig._FILENAMES[TowerShadingConfiguration]
            == "tower-shading.toml"
        )
