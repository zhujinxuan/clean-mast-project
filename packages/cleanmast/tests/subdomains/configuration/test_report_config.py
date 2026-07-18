from datetime import datetime

import pytest
from cleanmast.subdomains.configuration import (
    AnalysisWindow,
    DatasetConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
    MastRef,
)
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from pydantic import ValidationError


def _mast_ref(name: str) -> MastRef:
    """Create a minimal valid MastRef for testing."""
    return MastRef(
        name=name,
        air_density=1.225,
        input=TimeSeriesSource(data="/dev/null.parquet"),
    )


def _window(*mast_names: str) -> AnalysisWindow:
    """Create an AnalysisWindow covering the given mast names."""
    return AnalysisWindow(
        target_masts=list(mast_names),
        time_range=TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31)),
    )


class TestFlatReportConfig:
    """Tests for frozen FlatReportConfig and FlatSubsectionConfig."""

    def test_valid_minimal_config(self):
        config = FlatReportConfig(datasets=[], subsections=[])
        assert config.datasets == []
        assert config.subsections == []

    def test_subsection_validation(self):
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="a.b", type="wind_rose", datasets=["ds"])

    def test_duplicate_dataset_names_rejected(self):
        mast = _mast_ref("M1")
        win = _window("M1")
        datasets = [
            DatasetConfig(name="ds", masts=[mast], analysis_windows=[win]),
            DatasetConfig(name="ds", masts=[mast], analysis_windows=[win]),
        ]
        with pytest.raises(ValueError, match="Duplicate"):
            FlatReportConfig(datasets=datasets, subsections=[])

    def test_missing_dataset_reference_rejected(self):
        datasets = [
            DatasetConfig(
                name="ds",
                masts=[_mast_ref("M1")],
                analysis_windows=[_window("M1")],
            )
        ]
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["missing"])
        ]
        with pytest.raises(ValueError, match="dataset"):
            FlatReportConfig(datasets=datasets, subsections=subsections)

    def test_config_is_frozen(self):
        config = FlatReportConfig(datasets=[], subsections=[])
        with pytest.raises(ValidationError):
            config.datasets = []


class TestAnalysisWindowCoverage:
    """Tests for validate_analysis_window_coverage on DatasetConfig."""

    def test_empty_windows_rejected(self):
        with pytest.raises(ValueError, match="at least one window"):
            DatasetConfig(
                name="ds",
                masts=[_mast_ref("M1")],
                analysis_windows=[],
            )

    def test_mast_covered_by_multiple_windows_rejected(self):
        w1 = _window("M1")
        w2 = _window("M1")
        with pytest.raises(ValueError, match="multiple analysis windows"):
            DatasetConfig(
                name="ds",
                masts=[_mast_ref("M1")],
                analysis_windows=[w1, w2],
            )

    def test_unknown_target_mast_rejected(self):
        with pytest.raises(ValueError, match="not in dataset"):
            DatasetConfig(
                name="ds",
                masts=[_mast_ref("M1")],
                analysis_windows=[_window("M2")],
            )

    def test_uncovered_mast_rejected(self):
        with pytest.raises(ValueError, match="not covered by any"):
            DatasetConfig(
                name="ds",
                masts=[_mast_ref("M1"), _mast_ref("M2")],
                analysis_windows=[_window("M1")],
            )

    def test_single_window_single_mast_passes(self):
        cfg = DatasetConfig(
            name="ds",
            masts=[_mast_ref("M1")],
            analysis_windows=[_window("M1")],
        )
        assert cfg.name == "ds"
        assert len(cfg.analysis_windows) == 1

    def test_two_windows_grouped_passes(self):
        cfg = DatasetConfig(
            name="ds",
            masts=[_mast_ref("M1"), _mast_ref("M2")],
            analysis_windows=[_window("M1"), _window("M2")],
        )
        assert cfg.name == "ds"
        assert len(cfg.analysis_windows) == 2

    def test_no_masts_no_windows_rejected(self):
        """Dataset with no masts and empty windows — empty windows error fires."""
        with pytest.raises(ValueError, match="at least one window"):
            DatasetConfig(name="ds", analysis_windows=[])
