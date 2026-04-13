"""Tests for report configuration models."""

import tempfile
from pathlib import Path

import pytest
import tomli_w
from cleanmast.subdomains.assessment.domain.value_objects import (
    DocumentConfig,
    DocumentSectionConfig,
    MastConfig,
    RepTsReportConfig,
    SubsectionConfig,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestMastConfig:
    """Tests for MastConfig model."""
    
    def test_valid_config(self):
        """Test creating valid MastConfig."""
        config = MastConfig(
            name="M6002",
            air_density=1.225,
            input=TimeSeriesSource(data="./data.parquet")
        )
        
        assert config.name == "M6002"
        assert config.air_density == 1.225
        assert isinstance(config.input, TimeSeriesSource)
        assert config.input.data == "./data.parquet"
    
    def test_time_series_source_validation(self):
        """Test that input is validated as TimeSeriesSource."""
        config = MastConfig(
            name="M9773",
            air_density=1.003,
            input=TimeSeriesSource(data="./data.parquet")
        )
        assert config.input.data == "./data.parquet"
        assert config.input.sensors is None  # Optional for Parquet


class TestRepTsReportConfig:
    """Tests for RepTsReportConfig model."""
    
    def test_from_toml_with_new_format(self):
        """Test loading config from TOML format with masts in subsections."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            tomli_w.dump({
                "document": {
                    "section": [
                        {
                            "type": "timeseries",
                            "title": "Wind Speed Analysis",
                            "subsections": [
                                {
                                    "type": "timeseries",
                                    "title": "Monthly Wind",
                                    "masts": [
                                        {
                                            "name": "M6002",
                                            "air_density": 1.225,
                                            "input": {"data": "./data.parquet"}
                                        }
                                    ],
                                    "subsections": [
                                        {"type": "temporal"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }, f)
            f.flush()

            config = RepTsReportConfig.from_toml(Path(f.name))

            assert len(config.document.sections) == 1
            assert config.document.sections[0].type == "timeseries"
            assert config.document.sections[0].title == "Wind Speed Analysis"
            assert len(config.document.sections[0].subsections) == 1
            subsection = config.document.sections[0].subsections[0]
            assert subsection.type == "timeseries"
            assert subsection.masts is not None
            assert len(subsection.masts) == 1
            assert subsection.masts[0].name == "M6002"
            assert isinstance(subsection.masts[0].input, TimeSeriesSource)
            assert subsection.subsections is not None
            assert len(subsection.subsections) == 1
            assert subsection.subsections[0].type == "temporal"
    
    def test_from_toml_multiple_masts_and_sections(self):
        """Test loading config with multiple masts in subsections and document sections."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            tomli_w.dump({
                "document": {
                    "section": [
                        {
                            "type": "timeseries",
                            "title": "Section 1",
                            "subsections": [
                                {
                                    "type": "timeseries",
                                    "masts": [
                                        {"name": "M6002", "air_density": 1.225, "input": {"data": "./m1.parquet"}}
                                    ],
                                    "subsections": [
                                        {"type": "temporal"}
                                    ]
                                },
                                {
                                    "type": "timeseries",
                                    "masts": [
                                        {"name": "M9773", "air_density": 1.003, "input": {"data": "./m2.parquet"}}
                                    ],
                                    "subsections": [
                                        {"type": "wind_rose"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "timeseries",
                            "title": "Section 2",
                            "subsections": [
                                {"type": "weibull"}
                            ]
                        }
                    ]
                }
            }, f)
            f.flush()

            config = RepTsReportConfig.from_toml(Path(f.name))

            assert len(config.document.sections) == 2
            assert config.document.sections[0].title == "Section 1"
            assert config.document.sections[1].title == "Section 2"
            assert len(config.document.sections[0].subsections) == 2
            assert config.document.sections[0].subsections[0].type == "timeseries"
            assert config.document.sections[0].subsections[0].masts is not None
            assert config.document.sections[0].subsections[0].masts[0].name == "M6002"
            assert config.document.sections[0].subsections[1].masts is not None
            assert config.document.sections[0].subsections[1].masts[0].name == "M9773"
            assert len(config.document.sections[1].subsections) == 1
    
    def test_from_toml_minimal_format(self):
        """Test loading config with minimal TOML format (no sections)."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            tomli_w.dump({}, f)
            f.flush()
            
            config = RepTsReportConfig.from_toml(Path(f.name))
            
            assert config.document.sections == []
    
    def test_from_toml_section_without_subsections(self):
        """Test loading config with section but no subsections."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            tomli_w.dump({
                "document": {
                    "section": [
                        {
                            "type": "timeseries",
                            "title": "Analysis"
                        }
                    ]
                }
            }, f)
            f.flush()
            
            config = RepTsReportConfig.from_toml(Path(f.name))
            
            assert len(config.document.sections) == 1
            assert config.document.sections[0].subsections == []
    
    def test_from_toml_old_format_rejected(self):
        """Test that old TOML format (with data.masts at top level) is ignored."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            # Old format - masts at data level
            tomli_w.dump({
                "data": {
                    "masts": [
                        {
                            "name": "M6002",
                            "air_density": 1.225,
                            "input": {"data": "./data.parquet"}
                        }
                    ]
                }
            }, f)
            f.flush()
            
            config = RepTsReportConfig.from_toml(Path(f.name))
            
            assert config.document.sections == []
    
    def test_nested_subsections(self):
        """Test config with recursive nested subsections."""
        config = RepTsReportConfig(
            document=DocumentConfig(
                sections=[
                    DocumentSectionConfig(
                        type="timeseries",
                        title="Section 1",
                        subsections=[
                            SubsectionConfig(
                                type="timeseries",
                                title="Nested Container",
                                masts=[
                                    MastConfig(name="M6002", air_density=1.225, input=TimeSeriesSource(data="./m1.parquet"))
                                ],
                                subsections=[
                                    SubsectionConfig(
                                        type="temporal"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        )

        assert len(config.document.sections) == 1
        outer_sub = config.document.sections[0].subsections[0]
        assert outer_sub.type == "timeseries"
        assert outer_sub.masts is not None
        assert len(outer_sub.masts) == 1
        assert outer_sub.masts[0].name == "M6002"
        assert outer_sub.subsections is not None
        assert len(outer_sub.subsections) == 1
        inner_sub = outer_sub.subsections[0]
        assert inner_sub.type == "temporal"


class TestSubsectionConfig:
    """Tests for SubsectionConfig model."""
    
    def test_valid_type(self):
        """Test creating SubsectionConfig with valid type."""
        config = SubsectionConfig(type="temporal", title="Monthly Wind Analysis")
        
        assert config.type == "temporal"
        assert config.title == "Monthly Wind Analysis"
    
    def test_minimal_fields(self):
        """Test creating SubsectionConfig with only required type field."""
        config = SubsectionConfig(type="wind_rose")
        
        assert config.type == "wind_rose"
        assert config.title is None
        assert config.masts is None
        assert config.subsections is None
    
    def test_all_valid_types(self):
        valid_types = [
            "wind_rose",
            "vertical_profile",
            "wind_frequency",
            "weibull",
            "turbulence",
            "temporal",
        ]
        
        for subsection_type in valid_types:
            config = SubsectionConfig(type=subsection_type)
            assert config.type == subsection_type
    
    def test_timeseries_type_valid(self):
        """Test that 'timeseries' is accepted as a container subsection type."""
        config = SubsectionConfig(
            type="timeseries",
            masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
            subsections=[SubsectionConfig(type="temporal")]
        )
        assert config.type == "timeseries"
    
    def test_invalid_type_rejection(self):
        """Test that invalid subsection types are rejected."""
        with pytest.raises(ValueError) as exc_info:
            SubsectionConfig(type="invalid_type")
        
        assert "Invalid subsection type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)
    
    def test_with_masts(self):
        """Test creating SubsectionConfig with masts."""
        config = SubsectionConfig(
            type="timeseries",
            masts=[
                MastConfig(name="M6002", air_density=1.225, input=TimeSeriesSource(data="./data.parquet"))
            ],
            subsections=[SubsectionConfig(type="temporal")]
        )
        assert config.masts is not None
        assert len(config.masts) == 1
        assert config.masts[0].name == "M6002"

    def test_recursive_subsections(self):
        """Test creating SubsectionConfig with nested subsections."""
        config = SubsectionConfig(
            type="timeseries",
            masts=[
                MastConfig(name="M6002", air_density=1.225, input=TimeSeriesSource(data="./data.parquet"))
            ],
            subsections=[
                SubsectionConfig(type="temporal"),
                SubsectionConfig(type="wind_rose")
            ]
        )
        assert config.subsections is not None
        assert len(config.subsections) == 2
        assert config.subsections[0].type == "temporal"
        assert config.subsections[1].type == "wind_rose"

    def test_timeseries_without_masts_rejected(self):
        with pytest.raises(ValueError, match="must have at least one mast"):
            SubsectionConfig(type="timeseries", subsections=[SubsectionConfig(type="temporal")])

    def test_timeseries_without_subsections_rejected(self):
        with pytest.raises(ValueError, match="must have at least one nested subsection"):
            SubsectionConfig(type="timeseries", masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))])

    def test_leaf_with_masts_rejected(self):
        with pytest.raises(ValueError, match="must not have 'masts'"):
            SubsectionConfig(type="temporal", masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))])

    def test_leaf_with_subsections_rejected(self):
        with pytest.raises(ValueError, match="must not have 'subsections'"):
            SubsectionConfig(type="temporal", subsections=[SubsectionConfig(type="wind_rose")])

    def test_circular_reference_rejected(self):
        parent = SubsectionConfig.model_construct(
            type="timeseries",
            masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
            subsections=[]
        )
        child = SubsectionConfig.model_construct(
            type="timeseries",
            masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
            subsections=[parent]
        )
        parent.subsections = [child]
        with pytest.raises(ValueError, match="Circular reference"):
            SubsectionConfig(
                type="timeseries",
                masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
                subsections=[parent]
            )

    def test_nesting_depth_limit(self):
        inner = SubsectionConfig(
            type="timeseries",
            masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
            subsections=[SubsectionConfig(type="temporal")]
        )
        for _ in range(9):
            inner = SubsectionConfig(
                type="timeseries",
                masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
                subsections=[inner]
            )
        with pytest.raises(ValueError, match="maximum depth"):
            SubsectionConfig(
                type="timeseries",
                masts=[MastConfig(name="M1", air_density=1.225, input=TimeSeriesSource(data="./d.parquet"))],
                subsections=[inner]
            )


class TestDocumentSectionConfig:
    """Tests for DocumentSectionConfig model."""
    
    def test_valid_timeseries_section(self):
        """Test creating valid DocumentSectionConfig with timeseries type."""
        config = DocumentSectionConfig(
            type="timeseries",
            title="Wind Speed Analysis",
            subsections=[SubsectionConfig(type="temporal")]
        )
        
        assert config.type == "timeseries"
        assert config.title == "Wind Speed Analysis"
        assert len(config.subsections) == 1
        assert config.subsections[0].type == "temporal"
    
    def test_minimal_fields(self):
        """Test DocumentSectionConfig with only required type field."""
        config = DocumentSectionConfig(type="timeseries")
        
        assert config.type == "timeseries"
        assert config.title is None
        assert config.subsections == []


class TestDocumentConfig:
    """Tests for DocumentConfig model."""
    
    def test_valid_creation_with_sections(self):
        """Test creating DocumentConfig with sections."""
        config = DocumentConfig(
            sections=[
                DocumentSectionConfig(
                    type="timeseries",
                    title="Section 1",
                    subsections=[SubsectionConfig(type="temporal")]
                ),
                DocumentSectionConfig(
                    type="timeseries",
                    title="Section 2",
                    subsections=[SubsectionConfig(type="wind_rose")]
                )
            ]
        )
        
        assert len(config.sections) == 2
        assert config.sections[0].title == "Section 1"
        assert config.sections[1].title == "Section 2"
        assert config.sections[0].subsections[0].type == "temporal"
        assert config.sections[1].subsections[0].type == "wind_rose"
    
    def test_empty_sections_list(self):
        """Test DocumentConfig with empty sections list."""
        config = DocumentConfig()
        
        assert config.sections == []
    
    def test_empty_sections_explicit(self):
        """Test DocumentConfig with explicitly empty sections list."""
        config = DocumentConfig(sections=[])
        
        assert config.sections == []
