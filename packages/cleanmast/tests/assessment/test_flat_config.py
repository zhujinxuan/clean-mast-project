"""Tests for flat report configuration models (DatasetConfig, MastRef)."""

import os
import tempfile
from pathlib import Path

import pytest
import tomli
from cleanmast.subdomains.assessment.domain.value_objects import VALID_SUBSECTION_TYPES
from cleanmast.subdomains.assessment.domain.value_objects.dataset_config import (
    DatasetConfig,
    MastRef,
    MesoRef,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_report_config import (
    FlatReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_subsection_config import (
    FlatSubsectionConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.index_utils import (
    parse_index,
    sort_subsections,
)
from cleanmast.subdomains.assessment.domain.value_objects.tree_builder import (
    SectionNode,
    _collect_all_indices,
    _create_nodes,
    _fill_placeholder_siblings,
    _link_children,
    build_section_tree,
    flatten_tree,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from pydantic import ValidationError


class TestMastRef:
    """Tests for MastRef model."""

    def test_valid_mast_ref(self):
        """Test creating a valid MastRef."""
        mast = MastRef(
            name="M6002",
            air_density=1.225,
            input=TimeSeriesSource(data="./data.parquet"),
        )

        assert mast.name == "M6002"
        assert mast.air_density == 1.225
        assert mast.input.data == "./data.parquet"

    def test_missing_name_rejected(self):
        """Test that missing name field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MastRef(
                air_density=1.225,
                input=TimeSeriesSource(data="./data.parquet"),
            )

        assert "name" in str(exc_info.value)

    def test_negative_air_density_rejected(self):
        """Test that negative air_density is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MastRef(
                name="M6002",
                air_density=-0.5,
                input=TimeSeriesSource(data="./data.parquet"),
            )

        assert "air_density" in str(exc_info.value)

    def test_zero_air_density_rejected(self):
        """Test that zero air_density is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MastRef(
                name="M6002",
                air_density=0.0,
                input=TimeSeriesSource(data="./data.parquet"),
            )

        assert "air_density" in str(exc_info.value)


class TestMesoRef:
    """Tests for MesoRef model."""

    def test_valid_meso_ref(self):
        """Test creating a valid MesoRef."""
        meso = MesoRef(
            input=TimeSeriesSource(data="./meso/era5.parquet"),
            target_masts=["M6002", "M9773"],
        )

        assert meso.input.data == "./meso/era5.parquet"
        assert meso.target_masts == ["M6002", "M9773"]

    def test_single_target_mast(self):
        """Test MesoRef with a single target mast."""
        meso = MesoRef(
            input=TimeSeriesSource(data="./meso/era5.parquet"),
            target_masts=["M6002"],
        )

        assert meso.target_masts == ["M6002"]

    def test_empty_target_masts_rejected(self):
        """Test that empty target_masts list raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MesoRef(
                input=TimeSeriesSource(data="./meso/era5.parquet"),
                target_masts=[],
            )

        assert "target_masts" in str(exc_info.value)

    def test_missing_target_masts_rejected(self):
        """Test that missing target_masts field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MesoRef(
                input=TimeSeriesSource(data="./meso/era5.parquet"),
            )

        assert "target_masts" in str(exc_info.value)

    def test_missing_input_rejected(self):
        """Test that missing input field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MesoRef(
                target_masts=["M6002"],
            )

        assert "input" in str(exc_info.value)

    def test_serialization(self):
        """Test that valid MesoRef serializes correctly to dict."""
        meso = MesoRef(
            input=TimeSeriesSource(data="./meso/era5.parquet"),
            target_masts=["M6002"],
        )
        data = meso.model_dump()

        assert data["input"]["data"] == "./meso/era5.parquet"
        assert data["target_masts"] == ["M6002"]


class TestDatasetConfig:
    """Tests for DatasetConfig model."""

    def test_valid_config(self):
        """Test creating a valid DatasetConfig."""
        config = DatasetConfig(
            name="my-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data.parquet"),
                )
            ],
        )

        assert config.name == "my-dataset"
        assert config.masts[0].input.data == "./data.parquet"
        assert len(config.masts) == 1
        assert config.masts[0].name == "M6002"
        assert config.note is None

    def test_valid_config_with_note(self):
        """Test creating a valid DatasetConfig with optional note."""
        config = DatasetConfig(
            name="my-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data.parquet"),
                )
            ],
            note="A note about this dataset",
        )

        assert config.note == "A note about this dataset"

    def test_multiple_masts(self):
        """Test creating a DatasetConfig with multiple masts."""
        config = DatasetConfig(
            name="multi-mast-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data1.parquet"),
                ),
                MastRef(
                    name="M9773",
                    air_density=1.003,
                    input=TimeSeriesSource(data="./data2.parquet"),
                ),
            ],
        )

        assert len(config.masts) == 2
        assert config.masts[0].name == "M6002"
        assert config.masts[1].name == "M9773"

    def test_duplicate_mast_names_rejected(self):
        """Test that duplicate mast names within a dataset are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetConfig(
                name="my-dataset",
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data1.parquet"),
                    ),
                    MastRef(
                        name="M6002",
                        air_density=1.003,
                        input=TimeSeriesSource(data="./data2.parquet"),
                    ),
                ],
            )

        assert "duplicate" in str(exc_info.value).lower() or "name" in str(exc_info.value)

    def test_missing_name_rejected(self):
        """Test that missing name field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetConfig(
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data.parquet"),
                    )
                ],
            )

        assert "name" in str(exc_info.value)

    def test_missing_masts_rejected(self):
        """Test that missing masts field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetConfig(
                name="my-dataset",
            )

        assert "masts" in str(exc_info.value)

    def test_empty_masts_rejected(self):
        """Test that empty masts list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetConfig(
                name="my-dataset",
                masts=[],
            )

        assert "masts" in str(exc_info.value)

    def test_valid_config_with_mesos(self):
        """Test creating a DatasetConfig with mesos field."""
        config = DatasetConfig(
            name="my-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data.parquet"),
                )
            ],
            mesos=[
                MesoRef(
                    input=TimeSeriesSource(data="./meso/era5.parquet"),
                    target_masts=["M6002"],
                )
            ],
        )

        assert config.mesos is not None
        assert len(config.mesos) == 1
        assert config.mesos[0].input.data == "./meso/era5.parquet"
        assert config.mesos[0].target_masts == ["M6002"]

    def test_multiple_mesos(self):
        """Test DatasetConfig with multiple meso references."""
        config = DatasetConfig(
            name="my-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data.parquet"),
                )
            ],
            mesos=[
                MesoRef(
                    input=TimeSeriesSource(data="./meso/era5.parquet"),
                    target_masts=["M6002"],
                ),
                MesoRef(
                    input=TimeSeriesSource(data="./meso/merra2.parquet"),
                    target_masts=["M6002"],
                ),
            ],
        )

        assert len(config.mesos) == 2
        assert config.mesos[0].input.data == "./meso/era5.parquet"
        assert config.mesos[1].input.data == "./meso/merra2.parquet"

    def test_config_without_mesos(self):
        """Test that mesos field defaults to None when omitted."""
        config = DatasetConfig(
            name="my-dataset",
            masts=[
                MastRef(
                    name="M6002",
                    air_density=1.225,
                    input=TimeSeriesSource(data="./data.parquet"),
                )
            ],
        )

        assert config.mesos is None


class TestFlatSubsectionConfig:
    """Tests for FlatSubsectionConfig model."""

    def test_valid_minimal(self):
        """Test creating FlatSubsectionConfig with minimal required fields."""
        config = FlatSubsectionConfig(index="1", type="wind_rose", datasets=["repyear"])

        assert config.index == "1"
        assert config.type == "wind_rose"
        assert config.title is None
        assert config.datasets == ["repyear"]

    def test_valid_full(self):
        """Test creating FlatSubsectionConfig with all fields."""
        config = FlatSubsectionConfig(
            index="2.1",
            type="temporal",
            title="Monthly Wind Analysis",
            datasets=["repyear", "era5"],
        )

        assert config.index == "2.1"
        assert config.type == "temporal"
        assert config.title == "Monthly Wind Analysis"
        assert config.datasets == ["repyear", "era5"]

    def test_valid_index_single_digit(self):
        """Test valid index with single digit."""
        config = FlatSubsectionConfig(index="5", type="weibull", datasets=["repyear"])
        assert config.index == "5"

    def test_valid_index_multi_level(self):
        """Test valid index with multiple levels."""
        config = FlatSubsectionConfig(index="1.2.3.4", type="turbulence", datasets=["repyear"])
        assert config.index == "1.2.3.4"

    def test_invalid_index_empty(self):
        """Test that empty index is rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="", type="wind_rose")

    def test_invalid_index_non_numeric(self):
        """Test that non-numeric index is rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="a.b", type="wind_rose")

    def test_invalid_index_leading_dot(self):
        """Test that index with leading dot is rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index=".1.2", type="wind_rose")

    def test_invalid_index_trailing_dot(self):
        """Test that index with trailing dot is rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="1.2.", type="wind_rose")

    def test_invalid_index_double_dot(self):
        """Test that index with double dot is rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="1..2", type="wind_rose")

    def test_invalid_index_negative(self):
        """Test that negative numbers in index are rejected."""
        with pytest.raises(ValueError, match="index"):
            FlatSubsectionConfig(index="1.-2", type="wind_rose")

    def test_invalid_type(self):
        """Test that invalid subsection type is rejected."""
        with pytest.raises(ValueError, match="type"):
            FlatSubsectionConfig(index="1", type="invalid_type")

    def test_all_valid_types(self):
        """Test that all VALID_SUBSECTION_TYPES are accepted."""
        for i, subsection_type in enumerate(sorted(VALID_SUBSECTION_TYPES)):
            config = FlatSubsectionConfig(index=str(i), type=subsection_type, datasets=["repyear"])
            assert config.type == subsection_type

    def test_optional_fields_default_none(self):
        """Test that optional fields default to None."""
        config = FlatSubsectionConfig(index="3", type="air_density", datasets=["repyear"])

        assert config.title is None
        assert config.datasets == ["repyear"]

    def test_datasets_required(self):
        """Test that missing datasets field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FlatSubsectionConfig(index="1", type="wind_rose")

        assert "datasets" in str(exc_info.value)

    def test_empty_datasets_rejected(self):
        """Test that empty datasets list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=[])

        assert "datasets" in str(exc_info.value)

    def test_datasets_is_list_of_strings(self):
        """Test that valid list of strings is accepted for datasets."""
        config = FlatSubsectionConfig(index="1", type="wind_rose", datasets=["ds1"])

        assert config.datasets == ["ds1"]


class TestIndexSorting:
    """Tests for index parsing and numeric segment sorting."""

    def test_parse_index_simple(self):
        """Test parsing a simple single-segment index."""
        assert parse_index("3") == (3,)

    def test_parse_index_multi_segment(self):
        """Test parsing a multi-segment index."""
        assert parse_index("2.4.1") == (2, 4, 1)

    def test_parse_index_deep_nesting(self):
        """Test parsing deeply nested index."""
        assert parse_index("2.4.1.1.3") == (2, 4, 1, 1, 3)

    def test_parse_index_empty_string_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_index("")
        assert "empty" in str(exc_info.value).lower()

    def test_parse_index_empty_segment_raises(self):
        """Test that index with empty segment raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_index("2..4")
        assert "empty" in str(exc_info.value).lower() or "segment" in str(exc_info.value).lower()

    def test_parse_index_trailing_dot_raises(self):
        """Test that trailing dot raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_index("2.")
        assert "empty" in str(exc_info.value).lower() or "segment" in str(exc_info.value).lower()

    def test_sort_subsections_numeric_not_lexical(self):
        """Test that sorting is numeric, not lexical: 2.4.10 comes AFTER 2.4.2."""
        subsections = [
            FlatSubsectionConfig(index="2.4.10", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="weibull", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        indices = [s.index for s in result]
        assert indices == ["2.4.1", "2.4.2", "2.4.10"]

    def test_sort_subsections_mixed_depth(self):
        """Test sorting with mixed depth indices."""
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.5", type="timeseries", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        indices = [s.index for s in result]
        assert indices == ["2.4", "2.4.1", "2.4.2", "2.5"]

    def test_sort_subsections_first_segment_numeric(self):
        """Test that first segment is sorted numerically: 10.1 comes after 2.1."""
        subsections = [
            FlatSubsectionConfig(index="10.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.1", type="temporal", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        indices = [s.index for s in result]
        assert indices == ["2.1", "10.1"]

    def test_sort_subsections_single_segment(self):
        """Test sorting single-segment indices."""
        subsections = [
            FlatSubsectionConfig(index="3", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="1", type="temporal", datasets=["repyear"]),
            FlatSubsectionConfig(index="2", type="weibull", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        indices = [s.index for s in result]
        assert indices == ["1", "2", "3"]

    def test_sort_subsections_empty_list(self):
        """Test sorting empty list returns empty list."""
        result = sort_subsections([])
        assert result == []

    def test_sort_subsections_deep_nesting(self):
        """Test sorting deeply nested indices."""
        subsections = [
            FlatSubsectionConfig(index="2.4.1.2", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="temporal", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1.1", type="weibull", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        indices = [s.index for s in result]
        assert indices == ["2.4.1", "2.4.1.1", "2.4.1.2"]

    def test_sort_subsections_returns_new_list(self):
        """Test that sort_subsections returns a new list and doesn't mutate input."""
        subsections = [
            FlatSubsectionConfig(index="2", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="1", type="temporal", datasets=["repyear"]),
        ]
        result = sort_subsections(subsections)
        assert result is not subsections
        assert subsections[0].index == "2"
        assert subsections[1].index == "1"


class TestTreeBuilder:
    """Tests for SectionNode and build_section_tree."""

    def test_empty_input_returns_empty_list(self):
        result = build_section_tree([])
        assert result == []

    def test_single_subsection_no_nesting(self):
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", title="Wind Rose", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 1
        assert result[0].index == "1"
        assert result[0].type == "wind_rose"
        assert result[0].title == "Wind Rose"
        assert result[0].children == []

    def test_simple_parent_child(self):
        subsections = [
            FlatSubsectionConfig(index="2.4", type="timeseries", title="TS", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", title="WR", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        assert result[0].type == "timeseries"
        assert result[0].title == "Placeholder"
        root = result[1]
        assert root.index == "2"
        assert root.type == "timeseries"
        assert root.title == "Placeholder"
        assert len(root.children) == 4
        child_indices = [c.index for c in root.children]
        assert child_indices == ["2.1", "2.2", "2.3", "2.4"]
        parent = root.children[3]
        assert parent.index == "2.4"
        assert parent.title == "TS"
        assert len(parent.children) == 1
        assert parent.children[0].index == "2.4.1"
        assert parent.children[0].title == "WR"

    def test_auto_creates_placeholder_parent(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", title="WR", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        assert root.type == "timeseries"
        assert root.title == "Placeholder"
        assert len(root.children) == 4
        placeholder = root.children[3]
        assert placeholder.index == "2.4"
        assert placeholder.type == "timeseries"
        assert placeholder.title == "Placeholder"
        assert len(placeholder.children) == 1
        assert placeholder.children[0].index == "2.4.1"

    def test_siblings_at_same_level(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.5.1", type="temporal", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        assert len(root.children) == 5
        indices = [node.index for node in root.children]
        assert indices == ["2.1", "2.2", "2.3", "2.4", "2.5"]
        assert root.children[3].children[0].index == "2.4.1"
        assert root.children[4].children[0].index == "2.5.1"

    def test_multi_level_nesting(self):
        subsections = [
            FlatSubsectionConfig(index="2.4", type="timeseries", title="TS", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", title="WR", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.1.1", type="weibull", title="WB", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        assert len(root.children) == 4
        level1 = root.children[3]
        assert level1.index == "2.4"
        assert len(level1.children) == 1
        level2 = level1.children[0]
        assert level2.index == "2.4.1"
        assert len(level2.children) == 1
        level3 = level2.children[0]
        assert level3.index == "2.4.1.1"
        assert level3.title == "WB"

    def test_explicit_child_datasets_preserved(self):
        subsections = [
            FlatSubsectionConfig(
                index="2.4", type="timeseries", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.4.1", type="wind_rose", datasets=["repyear"]
            ),
        ]
        result = build_section_tree(subsections)
        root = result[1]
        assert root.index == "2"
        child = root.children[3].children[0]
        assert child.datasets == ["repyear"]

    def test_returns_sorted_tree(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.10.1", type="temporal", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.2", type="weibull", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        assert len(root.children) == 10
        indices = [node.index for node in root.children]
        assert indices == [
            "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10"
        ]
        assert root.children[3].children[0].index == "2.4.1"
        assert root.children[3].children[1].index == "2.4.2"
        assert root.children[9].children[0].index == "2.10.1"

    def test_deep_placeholder_chain(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1.1.1", type="wind_rose", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        assert root.type == "timeseries"
        assert root.title == "Placeholder"
        assert len(root.children) == 4
        level1 = root.children[3]
        assert level1.index == "2.4"
        assert level1.type == "timeseries"
        assert level1.title == "Placeholder"
        level2 = level1.children[0]
        assert level2.index == "2.4.1"
        assert level2.type == "timeseries"
        assert level2.title == "Placeholder"
        level3 = level2.children[0]
        assert level3.index == "2.4.1.1"
        assert level3.type == "timeseries"
        assert level3.title == "Placeholder"
        level4 = level3.children[0]
        assert level4.index == "2.4.1.1.1"
        assert level4.type == "wind_rose"

    def test_fills_root_level_placeholder_siblings(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.5.1", type="weibull", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        assert result[0].type == "timeseries"
        assert result[0].title == "Placeholder"
        root = result[1]
        assert root.index == "2"
        assert root.type == "timeseries"
        assert root.title == "Placeholder"
        assert len(root.children) == 5
        child_indices = [c.index for c in root.children]
        assert child_indices == ["2.1", "2.2", "2.3", "2.4", "2.5"]
        assert root.children[0].type == "timeseries"
        assert root.children[0].title == "Placeholder"
        assert root.children[1].type == "timeseries"
        assert root.children[1].title == "Placeholder"
        assert root.children[2].type == "timeseries"
        assert root.children[2].title == "Placeholder"
        assert root.children[3].children[0].index == "2.4.1"
        assert root.children[3].children[1].index == "2.4.2"
        assert root.children[4].children[0].index == "2.5.1"

    def test_fills_gap_within_children(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.3", type="temporal", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        root = result[1]
        assert root.index == "2"
        parent = root.children[3]
        assert parent.index == "2.4"
        assert len(parent.children) == 3
        assert parent.children[0].index == "2.4.1"
        assert parent.children[1].index == "2.4.2"
        assert parent.children[1].type == "timeseries"
        assert parent.children[1].title == "Placeholder"
        assert parent.children[2].index == "2.4.3"

    def test_sibling_fill_under_root_starting_at_one(self):
        subsections = [
            FlatSubsectionConfig(index="1.2.1", type="wind_rose", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 1
        assert result[0].index == "1"
        assert len(result[0].children) == 2
        assert result[0].children[0].index == "1.1"
        assert result[0].children[0].type == "timeseries"
        assert result[0].children[0].title == "Placeholder"
        assert result[0].children[1].index == "1.2"
        assert len(result[0].children[1].children) == 1
        assert result[0].children[1].children[0].index == "1.2.1"

    def test_single_segment_root_gaps(self):
        subsections = [
            FlatSubsectionConfig(index="3", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="5", type="temporal", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 5
        indices = [node.index for node in result]
        assert indices == ["1", "2", "3", "4", "5"]
        assert result[0].type == "timeseries"
        assert result[0].title == "Placeholder"
        assert result[1].type == "timeseries"
        assert result[1].title == "Placeholder"
        assert result[2].type == "wind_rose"
        assert result[3].type == "timeseries"
        assert result[3].title == "Placeholder"
        assert result[4].type == "temporal"

    def test_real_node_not_placeholder(self):
        """Real nodes from FlatSubsectionConfig should have is_placeholder=False."""
        subsections = [
            FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        root = result[1]
        real_node = root.children[3]
        assert real_node.index == "2.4"
        assert real_node.type == "timeseries"
        assert real_node.is_placeholder is False

    def test_placeholder_node_is_placeholder(self):
        """Auto-created placeholder nodes should have is_placeholder=True."""
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
        ]
        result = build_section_tree(subsections)
        root = result[1]
        placeholder = root.children[3]
        assert placeholder.index == "2.4"
        assert placeholder.type == "timeseries"
        assert placeholder.title == "Placeholder"
        assert placeholder.is_placeholder is True
        assert len(placeholder.children) == 1
        assert placeholder.children[0].index == "2.4.1"
        assert placeholder.children[0].is_placeholder is False

    def test_flatten_tree_roundtrip(self):
        """flatten_tree(build_section_tree(subsections)) should recover original subsections."""
        subsections = [
            FlatSubsectionConfig(
                index="2.4", type="timeseries", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.4.1", type="wind_rose", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.4.2",
                type="temporal",
                title="Monthly Stats",
                datasets=["repyear"],
            ),
            FlatSubsectionConfig(
                index="2.4.3", type="weibull", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.4.4",
                type="turbulence",
                datasets=["repyear", "era5"],
            ),
            FlatSubsectionConfig(
                index="2.5", type="timeseries", datasets=["era5"]
            ),
            FlatSubsectionConfig(
                index="2.5.1", type="wind_rose", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.5.2", type="vertical_profile", datasets=["era5"]
            ),
            FlatSubsectionConfig(
                index="2.5.3", type="wind_frequency", datasets=["era5"]
            ),
            FlatSubsectionConfig(
                index="2.6",
                type="fifty_year_max_wind",
                datasets=["repyear"],
            ),
            FlatSubsectionConfig(
                index="2.6.1", type="air_density", datasets=["repyear"]
            ),
            FlatSubsectionConfig(
                index="2.6.2", type="wind_rose", datasets=["repyear"]
            ),
        ]
        tree = build_section_tree(subsections)
        flat = flatten_tree(tree)

        assert len(flat) == 12

        orig_by_idx = {s.index: s for s in subsections}
        flat_by_idx = {s.index: s for s in flat}

        for idx in orig_by_idx:
            assert idx in flat_by_idx, f"Missing index {idx} in flattened output"
            o = orig_by_idx[idx]
            f = flat_by_idx[idx]
            assert o.type == f.type, f"Type mismatch at {idx}"
            assert o.title == f.title, f"Title mismatch at {idx}"
            assert o.datasets == f.datasets, f"Datasets mismatch at {idx}"

    def test_flatten_tree_excludes_placeholders(self):
        """Placeholder nodes should not appear in flattened output."""
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            FlatSubsectionConfig(index="2.4.3", type="temporal", datasets=["repyear"]),
        ]
        tree = build_section_tree(subsections)
        flat = flatten_tree(tree)

        flat_indices = [s.index for s in flat]
        assert "2.4.1" in flat_indices
        assert "2.4.3" in flat_indices
        assert "2.4.2" not in flat_indices, "Placeholder 2.4.2 should be excluded"


class TestFlatReportConfig:
    """Tests for FlatReportConfig model."""

    def test_valid_minimal_config(self):
        """Test creating a valid FlatReportConfig with empty lists."""
        config = FlatReportConfig(datasets=[], subsections=[])

        assert config.datasets == []
        assert config.subsections == []
        assert config.tree == []

    def test_valid_config_with_datasets_and_subsections(self):
        """Test creating a valid config with datasets and subsections."""
        datasets = [
            DatasetConfig(
                name="repyear",
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data/repyear.parquet"),
                    )
                ],
            ),
        ]
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["repyear"]),
        ]
        config = FlatReportConfig(datasets=datasets, subsections=subsections)

        assert len(config.datasets) == 1
        assert config.datasets[0].name == "repyear"
        assert len(config.subsections) == 1
        assert config.subsections[0].index == "1"

    def test_duplicate_dataset_names_rejected(self):
        """Test that duplicate dataset names are rejected."""
        datasets = [
            DatasetConfig(
                name="repyear",
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data1.parquet"),
                    )
                ],
            ),
            DatasetConfig(
                name="repyear",
                masts=[
                    MastRef(
                        name="M9773",
                        air_density=1.003,
                        input=TimeSeriesSource(data="./data2.parquet"),
                    )
                ],
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            FlatReportConfig(datasets=datasets, subsections=[])

        assert "duplicate" in str(exc_info.value).lower()

    def test_missing_dataset_reference_rejected(self):
        """Test that subsection referencing nonexistent dataset is rejected."""
        datasets = [
            DatasetConfig(
                name="repyear",
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data.parquet"),
                    )
                ],
            ),
        ]
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["nonexistent"]),
        ]
        with pytest.raises(ValidationError) as exc_info:
            FlatReportConfig(datasets=datasets, subsections=subsections)

        assert "dataset" in str(exc_info.value).lower()

    def test_tree_property_builds_section_tree(self):
        """Test that tree property calls build_section_tree on sorted subsections."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["repyear"]),
            ],
        )
        tree = config.tree

        assert len(tree) == 2
        assert tree[0].index == "1"
        assert tree[1].index == "2"
        assert len(tree[1].children) == 4
        assert tree[1].children[3].index == "2.4"
        assert len(tree[1].children[3].children) == 1
        assert tree[1].children[3].children[0].index == "2.4.1"

    def test_from_toml_loads_config(self):
        """Test loading config from TOML file."""
        toml_content = b"""
[[datasets]]
name = "repyear"

[[datasets.masts]]
name = "M6002"
air_density = 1.225

[datasets.masts.input]
data = "./data/repyear.parquet"

[[subsections]]
index = "1"
type = "wind_rose"
datasets = ["repyear"]
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "report.toml"
            config_path.write_bytes(toml_content)
            config = FlatReportConfig.from_toml(config_path)

        assert len(config.datasets) == 1
        assert config.datasets[0].name == "repyear"
        # Data path is resolved relative to config directory
        assert config.datasets[0].masts[0].input.data.endswith(
            "/data/repyear.parquet"
        )
        assert len(config.subsections) == 1
        assert config.subsections[0].index == "1"
        assert config.subsections[0].datasets == ["repyear"]

    def test_from_toml_resolves_paths_relative_to_config_dir(self):
        """Test that dataset paths are resolved relative to config file directory."""
        toml_content = b"""
[[datasets]]
name = "repyear"

[[datasets.masts]]
name = "M6002"
air_density = 1.225

[datasets.masts.input]
data = "data/repyear.parquet"

[[subsections]]
index = "1"
type = "wind_rose"
datasets = ["repyear"]
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "configs"
            config_dir.mkdir()
            config_path = config_dir / "report.toml"
            config_path.write_bytes(toml_content)
            config = FlatReportConfig.from_toml(config_path)

        assert config.datasets[0].masts[0].input.data == "data/repyear.parquet"

    def test_to_toml_serializes_config(self):
        """Test serializing config to TOML file."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(index="1", type="wind_rose", datasets=["repyear"]),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.toml"
            config.to_toml(output_path)
            content = output_path.read_text(encoding="utf-8")

        assert "[[datasets]]" in content
        assert 'name = "repyear"' in content
        assert "[[subsections]]" in content
        assert 'index = "1"' in content

    def test_to_toml_roundtrip(self):
        """Test that to_toml produces output parseable by from_toml."""
        original = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(index="1", type="wind_rose", datasets=["repyear"]),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.toml"
            original.to_toml(output_path)
            restored = FlatReportConfig.from_toml(output_path)

        assert len(restored.datasets) == 1
        assert restored.datasets[0].name == "repyear"
        assert len(restored.subsections) == 1
        assert restored.subsections[0].index == "1"


class TestConfigRoundTrip:
    """Comprehensive round-trip tests for FlatReportConfig TOML serialization."""

    def _roundtrip(self, config: FlatReportConfig) -> FlatReportConfig:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False, encoding="utf-8") as f:
            temp_path = Path(f.name)
        try:
            config.to_toml(temp_path)
            return FlatReportConfig.from_toml(temp_path)
        finally:
            os.unlink(temp_path)

    def _assert_subsections_equal(
        self,
        original: list[FlatSubsectionConfig],
        restored: list[FlatSubsectionConfig],
    ) -> None:
        assert len(original) == len(restored)
        for o, r in zip(original, restored):
            assert o.index == r.index
            assert o.type == r.type
            assert o.title == r.title
            assert o.datasets == r.datasets

    def _assert_tree_equal(
        self,
        tree1: list[SectionNode],
        tree2: list[SectionNode],
    ) -> None:
        assert len(tree1) == len(tree2)
        for n1, n2 in zip(tree1, tree2):
            assert n1.index == n2.index
            assert n1.type == n2.type
            assert n1.title == n2.title
            assert n1.datasets == n2.datasets
            self._assert_tree_equal(n1.children, n2.children)

    def test_roundtrip_basic_structure(self):
        """Write config to TOML, read back, verify structure identical."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="1", type="wind_rose", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2", type="temporal", title="Monthly Analysis", datasets=["repyear"]
                ),
            ],
        )
        restored = self._roundtrip(config)
        self._assert_subsections_equal(config.subsections, restored.subsections)
        self._assert_tree_equal(config.tree, restored.tree)
        assert len(restored.datasets) == 1
        assert restored.datasets[0].name == "repyear"

    def test_roundtrip_toml_syntactically_valid(self):
        """Verify written TOML is parseable by tomli."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="1", type="wind_rose", datasets=["repyear"]
                ),
            ],
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False, encoding="utf-8"
        ) as f:
            temp_path = Path(f.name)
        try:
            config.to_toml(temp_path)
            with open(temp_path, "rb") as f:
                data = tomli.load(f)
            assert "datasets" in data
            assert "subsections" in data
            assert len(data["datasets"]) == 1
            assert len(data["subsections"]) == 1
        finally:
            os.unlink(temp_path)

    def test_roundtrip_all_subsection_types(self):
        """Test round-trip with all valid subsection types represented."""
        datasets = [
            DatasetConfig(
                name="ds",
                masts=[
                    MastRef(
                        name="M6002",
                        air_density=1.225,
                        input=TimeSeriesSource(data="./data/ds.parquet"),
                    )
                ],
            ),
        ]
        subsections = []
        for i, stype in enumerate(sorted(VALID_SUBSECTION_TYPES)):
            subsections.append(
                FlatSubsectionConfig(
                    index=str(i + 1),
                    type=stype,
                    datasets=["ds"],
                )
            )
        config = FlatReportConfig(datasets=datasets, subsections=subsections)
        restored = self._roundtrip(config)
        self._assert_subsections_equal(config.subsections, restored.subsections)
        assert len(restored.subsections) == len(VALID_SUBSECTION_TYPES)
        restored_types = {s.type for s in restored.subsections}
        assert restored_types == VALID_SUBSECTION_TYPES

    def test_roundtrip_dataset_inheritance(self):
        """Test that dataset inheritance survives round-trip."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.4", type="timeseries", datasets=["repyear"]
                ),
                FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
            ],
        )
        restored = self._roundtrip(config)
        assert restored.subsections[1].datasets == ["repyear"]
        orig_tree = config.tree
        rest_tree = restored.tree
        self._assert_tree_equal(orig_tree, rest_tree)
        assert rest_tree[1].children[3].children[0].datasets == ["repyear"]

    def test_roundtrip_explicit_dataset_override(self):
        """Test that explicit dataset override survives round-trip."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
                DatasetConfig(
                    name="era5",
                    masts=[
                        MastRef(
                            name="M9773",
                            air_density=1.003,
                            input=TimeSeriesSource(data="./data/era5.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.4", type="timeseries", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.4.1", type="wind_rose", datasets=["era5"]
                ),
            ],
        )
        restored = self._roundtrip(config)
        orig_tree = config.tree
        rest_tree = restored.tree
        self._assert_tree_equal(orig_tree, rest_tree)
        assert rest_tree[1].children[3].children[0].datasets == ["era5"]

    def test_roundtrip_fifty_year_children(self):
        """Test round-trip with fifty-year max wind children (2.6.1-2.6.5)."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.6",
                    type="fifty_year_max_wind",
                    datasets=["repyear"],
                ),
                FlatSubsectionConfig(index="2.6.1", type="air_density", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.2", type="wind_rose", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.3", type="turbulence", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.4", type="temporal", datasets=["repyear"]),
                FlatSubsectionConfig(
                    index="2.6.5", type="representative_year_calibration", datasets=["repyear"]
                ),
            ],
        )
        restored = self._roundtrip(config)
        self._assert_subsections_equal(config.subsections, restored.subsections)
        orig_tree = config.tree
        rest_tree = restored.tree
        self._assert_tree_equal(orig_tree, rest_tree)
        assert len(rest_tree) == 2
        assert rest_tree[0].index == "1"
        root = rest_tree[1]
        assert root.index == "2"
        assert len(root.children) == 6
        real_node = root.children[5]
        assert real_node.index == "2.6"
        assert real_node.type == "fifty_year_max_wind"
        assert len(real_node.children) == 5
        child_indices = [c.index for c in real_node.children]
        assert child_indices == [
            "2.6.1",
            "2.6.2",
            "2.6.3",
            "2.6.4",
            "2.6.5",
        ]

    def test_roundtrip_multi_dataset_declaration(self):
        """Test round-trip with subsections referencing multiple datasets."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
                DatasetConfig(
                    name="era5",
                    masts=[
                        MastRef(
                            name="M9773",
                            air_density=1.003,
                            input=TimeSeriesSource(data="./data/era5.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="1", type="wind_rose", datasets=["repyear", "era5"]
                ),
                FlatSubsectionConfig(
                    index="2", type="temporal", datasets=["repyear", "era5"]
                ),
            ],
        )
        restored = self._roundtrip(config)
        self._assert_subsections_equal(config.subsections, restored.subsections)
        assert restored.subsections[0].datasets == ["repyear", "era5"]
        assert restored.subsections[1].datasets == ["repyear", "era5"]

    def test_roundtrip_realistic_config(self):
        """Test round-trip with realistic config: 2 datasets, 12 subsections."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
                DatasetConfig(
                    name="era5",
                    masts=[
                        MastRef(
                            name="M9773",
                            air_density=1.003,
                            input=TimeSeriesSource(data="./data/era5.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.4", type="timeseries", datasets=["repyear"]
                ),
                FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
                FlatSubsectionConfig(
                    index="2.4.2", type="temporal", title="Monthly Stats", datasets=["repyear"]
                ),
                FlatSubsectionConfig(index="2.4.3", type="weibull", datasets=["repyear"]),
                FlatSubsectionConfig(
                    index="2.4.4",
                    type="turbulence",
                    datasets=["repyear", "era5"],
                ),
                FlatSubsectionConfig(
                    index="2.5", type="timeseries", datasets=["era5"]
                ),
                FlatSubsectionConfig(
                    index="2.5.1", type="wind_rose", datasets=["repyear"]
                ),
                FlatSubsectionConfig(index="2.5.2", type="vertical_profile", datasets=["era5"]),
                FlatSubsectionConfig(index="2.5.3", type="wind_frequency", datasets=["era5"]),
                FlatSubsectionConfig(
                    index="2.6",
                    type="fifty_year_max_wind",
                    datasets=["repyear"],
                ),
                FlatSubsectionConfig(index="2.6.1", type="air_density", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.2", type="wind_rose", datasets=["repyear"]),
            ],
        )
        restored = self._roundtrip(config)
        self._assert_subsections_equal(config.subsections, restored.subsections)
        orig_tree = config.tree
        rest_tree = restored.tree
        self._assert_tree_equal(orig_tree, rest_tree)
        assert len(restored.datasets) == 2
        assert len(restored.subsections) == 12
        assert len(rest_tree) == 2
        assert rest_tree[0].index == "1"
        root = rest_tree[1]
        assert root.index == "2"
        assert len(root.children) == 6
        assert len(root.children[3].children) == 4
        assert len(root.children[4].children) == 3
        assert len(root.children[5].children) == 2


class TestTreeIsomorphism:
    """Tests for Flat ↔ Tree isomorphism (round-trip without TOML)."""

    def test_flat_to_tree_to_flat_identical(self):
        """Round-trip Flat → Tree → Flat produces identical FlatSubsectionConfig list."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
                DatasetConfig(
                    name="era5",
                    masts=[
                        MastRef(
                            name="M9773",
                            air_density=1.003,
                            input=TimeSeriesSource(data="./data/era5.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.4", type="timeseries", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.4.1", type="wind_rose", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.4.2",
                    type="temporal",
                    title="Monthly Stats",
                    datasets=["repyear"],
                ),
                FlatSubsectionConfig(
                    index="2.4.3", type="weibull", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.4.4",
                    type="turbulence",
                    datasets=["repyear", "era5"],
                ),
                FlatSubsectionConfig(
                    index="2.5", type="timeseries", datasets=["era5"]
                ),
                FlatSubsectionConfig(
                    index="2.5.1", type="wind_rose", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.5.2", type="vertical_profile", datasets=["era5"]
                ),
                FlatSubsectionConfig(
                    index="2.5.3", type="wind_frequency", datasets=["era5"]
                ),
                FlatSubsectionConfig(
                    index="2.6",
                    type="fifty_year_max_wind",
                    datasets=["repyear"],
                ),
                FlatSubsectionConfig(
                    index="2.6.1", type="air_density", datasets=["repyear"]
                ),
                FlatSubsectionConfig(
                    index="2.6.2", type="wind_rose", datasets=["repyear"]
                ),
            ],
        )
        tree = build_section_tree(config.subsections)
        flat = flatten_tree(tree)

        assert len(flat) == len(config.subsections)
        flat_by_index = {s.index: s for s in flat}
        for orig in config.subsections:
            assert orig.index in flat_by_index
            restored = flat_by_index[orig.index]
            assert restored.type == orig.type
            assert restored.title == orig.title
            assert restored.datasets == orig.datasets

    def test_placeholder_nodes_excluded_from_flat(self):
        """Placeholder nodes created by build_section_tree must NOT appear in flattened output."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.4.3", type="temporal", datasets=["repyear"]),
            ],
        )
        tree = build_section_tree(config.subsections)
        flat = flatten_tree(tree)

        assert len(flat) == 2
        flat_indices = {s.index for s in flat}
        assert "2.4.2" not in flat_indices
        assert "2.4.1" in flat_indices
        assert "2.4.3" in flat_indices

    def test_deeply_nested_roundtrip(self):
        """3+ level nesting survives Flat → Tree → Flat round-trip."""
        config = FlatReportConfig(
            datasets=[
                DatasetConfig(
                    name="repyear",
                    masts=[
                        MastRef(
                            name="M6002",
                            air_density=1.225,
                            input=TimeSeriesSource(data="./data/repyear.parquet"),
                        )
                    ],
                ),
            ],
            subsections=[
                FlatSubsectionConfig(
                    index="2.6",
                    type="fifty_year_max_wind",
                    datasets=["repyear"],
                ),
                FlatSubsectionConfig(index="2.6.1", type="air_density", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.1.1", type="iec_standards", datasets=["repyear"]),
                FlatSubsectionConfig(index="2.6.1.2", type="fifty_year_method1", datasets=["repyear"]),
            ],
        )
        tree = build_section_tree(config.subsections)
        flat = flatten_tree(tree)

        assert len(flat) == 4
        flat_by_index = {s.index: s for s in flat}
        assert "2.6" in flat_by_index
        assert flat_by_index["2.6"].type == "fifty_year_max_wind"
        assert "2.6.1" in flat_by_index
        assert flat_by_index["2.6.1"].type == "air_density"
        assert "2.6.1.1" in flat_by_index
        assert flat_by_index["2.6.1.1"].type == "iec_standards"
        assert "2.6.1.2" in flat_by_index
        assert flat_by_index["2.6.1.2"].type == "fifty_year_method1"


class TestCollectAllIndices:
    """Tests for _collect_all_indices function."""

    def test_collect_all_indices_with_parents(self):
        """actual={2.4, 2.4.1} → result contains {2, 2.4, 2.4.1}."""
        actual = {
            "2.4": FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["repyear"]),
            "2.4.1": FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["repyear"]),
        }
        result = _collect_all_indices(actual)
        assert result == {"2", "2.4", "2.4.1"}

    def test_collect_all_indices_single_segment(self):
        """actual={1} → result contains {1} (no parents to derive)."""
        actual = {
            "1": FlatSubsectionConfig(index="1", type="wind_rose", datasets=["repyear"]),
        }
        result = _collect_all_indices(actual)
        assert result == {"1"}

    def test_collect_all_indices_deep_nesting(self):
        """actual={3.1.2} → result contains {3, 3.1, 3.1.2}."""
        actual = {
            "3.1.2": FlatSubsectionConfig(index="3.1.2", type="weibull", datasets=["repyear"]),
        }
        result = _collect_all_indices(actual)
        assert result == {"3", "3.1", "3.1.2"}


class TestCreateNodes:
    """Tests for _create_nodes function."""

    def test_real_index_creates_non_placeholder(self):
        """Real index from config → SectionNode with correct attrs, no is_placeholder."""
        actual = {
            "2.4": FlatSubsectionConfig(
                index="2.4", type="timeseries", title="TS", datasets=["ds1"]
            ),
        }
        nodes = _create_nodes({"2.4"}, actual)
        assert "2.4" in nodes
        node = nodes["2.4"]
        assert node.index == "2.4"
        assert node.type == "timeseries"
        assert node.title == "TS"
        assert node.datasets == ["ds1"]
        assert node.is_placeholder is False

    def test_missing_index_creates_placeholder(self):
        """Missing index → SectionNode with is_placeholder=True."""
        nodes = _create_nodes({"2"}, {})
        assert "2" in nodes
        node = nodes["2"]
        assert node.index == "2"
        assert node.type == "timeseries"
        assert node.title == "Placeholder"
        assert node.datasets is None
        assert node.is_placeholder is True

    def test_empty_inputs_returns_empty_dict(self):
        """Empty inputs → returns empty dict."""
        nodes = _create_nodes(set(), {})
        assert nodes == {}


class TestLinkChildren:
    """Tests for _link_children function."""

    def test_links_parent_and_child(self):
        """nodes {2(placeholder), 2.4(real), 2.4.1(real)} → roots=[2], 2.4 child of 2."""
        nodes = {
            "2": SectionNode(index="2", type="timeseries", is_placeholder=True),
            "2.4": SectionNode(index="2.4", type="timeseries"),
            "2.4.1": SectionNode(index="2.4.1", type="wind_rose"),
        }
        roots = _link_children(nodes)
        assert len(roots) == 1
        assert roots[0].index == "2"
        assert len(roots[0].children) == 1
        assert roots[0].children[0].index == "2.4"
        assert len(roots[0].children[0].children) == 1
        assert roots[0].children[0].children[0].index == "2.4.1"

    def test_single_node_no_children(self):
        """nodes {1(real)} → roots=[1], no children."""
        nodes = {
            "1": SectionNode(index="1", type="wind_rose"),
        }
        roots = _link_children(nodes)
        assert len(roots) == 1
        assert roots[0].index == "1"
        assert roots[0].children == []

    def test_orphan_becomes_root(self):
        """orphan child (parent not in nodes) → child becomes root."""
        nodes = {
            "2.4": SectionNode(index="2.4", type="timeseries"),
        }
        roots = _link_children(nodes)
        assert len(roots) == 1
        assert roots[0].index == "2.4"
        assert roots[0].children == []


class TestFillPlaceholderSiblings:
    """Tests for _fill_placeholder_siblings function."""

    def test_fills_gaps(self):
        """siblings [2.4, 2.6] → [2.1, 2.2, 2.3, 2.4, 2.5, 2.6]."""
        siblings = [
            SectionNode(index="2.4", type="timeseries"),
            SectionNode(index="2.6", type="temporal"),
        ]
        result = _fill_placeholder_siblings(siblings)
        indices = [n.index for n in result]
        assert indices == ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]
        assert result[0].is_placeholder is True
        assert result[1].is_placeholder is True
        assert result[2].is_placeholder is True
        assert result[3].is_placeholder is False
        assert result[4].is_placeholder is True
        assert result[5].is_placeholder is False

    def test_empty_input(self):
        """empty input → []."""
        result = _fill_placeholder_siblings([])
        assert result == []

    def test_already_complete(self):
        """already-complete [1, 2, 3] → unchanged."""
        siblings = [
            SectionNode(index="1", type="wind_rose"),
            SectionNode(index="2", type="temporal"),
            SectionNode(index="3", type="weibull"),
        ]
        result = _fill_placeholder_siblings(siblings)
        indices = [n.index for n in result]
        assert indices == ["1", "2", "3"]
        assert all(not n.is_placeholder for n in result)

    def test_nested_level_gaps(self):
        """gaps at nested level [2.4.1, 2.4.3] under parent 2.4 → [2.4.1, 2.4.2, 2.4.3]."""
        siblings = [
            SectionNode(index="2.4.1", type="wind_rose"),
            SectionNode(index="2.4.3", type="temporal"),
        ]
        result = _fill_placeholder_siblings(siblings)
        indices = [n.index for n in result]
        assert indices == ["2.4.1", "2.4.2", "2.4.3"]
        assert result[0].is_placeholder is False
        assert result[1].is_placeholder is True
        assert result[1].index == "2.4.2"
        assert result[2].is_placeholder is False
