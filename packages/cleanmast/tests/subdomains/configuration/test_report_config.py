import pytest
from cleanmast.subdomains.configuration import (
    DatasetConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
)
from pydantic import ValidationError


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
        datasets = [DatasetConfig(name="ds"), DatasetConfig(name="ds")]
        with pytest.raises(ValueError, match="Duplicate"):
            FlatReportConfig(datasets=datasets, subsections=[])

    def test_missing_dataset_reference_rejected(self):
        datasets = [DatasetConfig(name="ds")]
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["missing"])
        ]
        with pytest.raises(ValueError, match="dataset"):
            FlatReportConfig(datasets=datasets, subsections=subsections)

    def test_config_is_frozen(self):
        config = FlatReportConfig(datasets=[], subsections=[])
        with pytest.raises(ValidationError):
            config.datasets = []
