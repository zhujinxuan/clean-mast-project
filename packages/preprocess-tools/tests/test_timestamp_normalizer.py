"""Tests for timestamp normalizer functionality."""

import tempfile
from pathlib import Path

import polars as pl
import pytest
from preprocess_tools.timestamp_normalizer import (
    TimestampNormalizerConfig,
    load_config,
    normalize_timestamp,
    process_file,
)


@pytest.fixture
def fixtures_dir():
    """Get path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def csv_files_dir(fixtures_dir):
    """Get path to CSV files directory."""
    return fixtures_dir / "csv_files"


@pytest.fixture
def configs_dir(fixtures_dir):
    """Get path to configs directory."""
    return fixtures_dir / "configs"


@pytest.fixture
def temp_output_dir():
    """Create temporary directory for outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestConfigLoading:
    """Tests for configuration loading and validation."""

    def test_load_valid_config(self, configs_dir):
        """Test loading a valid configuration file."""
        config_path = configs_dir / "timestamp_normalizer.toml"
        config = load_config(str(config_path))

        assert isinstance(config, TimestampNormalizerConfig)
        assert config.input_path == "../csv_files/simple.csv"
        assert config.timestamp_column == "DateTime"
        assert config.input_format == "%Y-%m-%d %H:%M:%S"
        assert config.output_format == "%Y-%m-%d %H:%M:%S"

    def test_load_nonexistent_config(self):
        """Test loading non-existent config file."""
        with pytest.raises(SystemExit):
            load_config("nonexistent.toml")


class TestTimestampNormalization:
    """Tests for timestamp normalization logic."""

    def test_normalize_with_explicit_format(self):
        """Test normalizing timestamps with explicit format."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"
        assert result["DateTime"][1] == "2024-01-01 00:10:00"

    def test_normalize_with_auto_format(self):
        """Test normalizing timestamps with auto-detection."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="auto",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"

    def test_normalize_format_conversion(self):
        """Test converting timestamp from one format to another."""
        df = pl.DataFrame({
            "DateTime": ["01/01/2024 00:00:00", "01/01/2024 00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%d/%m/%Y %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"
        assert result["DateTime"][1] == "2024-01-01 00:10:00"

    def test_normalize_date_only_format(self):
        """Test normalizing date-only timestamps."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01", "2024-01-02"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"

    def test_normalize_custom_output_format(self):
        """Test normalizing with custom output format."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%d/%m/%Y %H:%M"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "01/01/2024 00:00"
        assert result["DateTime"][1] == "01/01/2024 00:10"

    def test_normalize_iso_format(self):
        """Test normalizing ISO 8601 format."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01T00:00:00", "2024-01-01T00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="auto",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"

    def test_normalize_missing_column(self):
        """Test error when timestamp column doesn't exist."""
        df = pl.DataFrame({
            "OtherColumn": ["2024-01-01 00:00:00"],
            "WindSpeed": [5.2]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="NonexistentColumn",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        with pytest.raises(SystemExit):
            normalize_timestamp(df, config)

    def test_normalize_preserves_other_columns(self):
        """Test that other columns are preserved unchanged."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": [5.2, 5.5],
            "WindDirection": [180.5, 182.3],
            "Status": ["OK", "OK"]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["WindSpeed"][0] == 5.2
        assert result["WindDirection"][0] == 180.5
        assert result["Status"][0] == "OK"
        assert len(result.columns) == 4


class TestFileProcessing:
    """Integration tests for file processing."""

    def test_process_complete_file(self, configs_dir, temp_output_dir):
        """Test processing a complete file with all steps."""
        config = load_config(str(configs_dir / "timestamp_normalizer.toml"))
        config.output_path = str(temp_output_dir / "normalized.csv")

        process_file(config, configs_dir)

        output_file = Path(config.output_path)
        assert output_file.exists()

        result = pl.read_csv(output_file)
        assert "DateTime" in result.columns
        assert len(result) == 5

    def test_process_nonexistent_file(self, configs_dir):
        """Test error when input file doesn't exist."""
        config = load_config(str(configs_dir / "timestamp_normalizer.toml"))
        config.input_path = "nonexistent.csv"

        with pytest.raises(SystemExit):
            process_file(config, configs_dir)

    def test_process_tab_delimited(self, csv_files_dir, temp_output_dir):
        """Test processing tab-delimited file."""
        config = TimestampNormalizerConfig(
            input_path=str(csv_files_dir / "tab_delimited.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            timestamp_column="Timestamp",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S",
            delimiter="\t"
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert "Timestamp" in result.columns
        assert len(result) == 3

    def test_process_with_skip_rows(self, csv_files_dir, temp_output_dir):
        """Test processing file with skip_rows."""
        config = TimestampNormalizerConfig(
            input_path=str(csv_files_dir / "with_header_rows.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            timestamp_column="Timestamp",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S",
            skip_rows=3
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert "Timestamp" in result.columns
        assert len(result) == 3


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_single_timestamp(self):
        """Test with single timestamp row."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00"],
            "WindSpeed": [5.2]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert len(result) == 1
        assert result["DateTime"][0] == "2024-01-01 00:00:00"

    def test_microseconds_format(self):
        """Test timestamps with microseconds."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00.123456", "2024-01-01 00:10:00.654321"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="auto",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        # Microseconds should be dropped in output
        assert result["DateTime"][0] == "2024-01-01 00:00:00"

    def test_year_only_format(self):
        """Test with year-only format."""
        df = pl.DataFrame({
            "DateTime": ["2024", "2025"],
            "Value": [1.0, 2.0]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y",
            output_format="%Y-%m-%d"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01"

    def test_mixed_format_with_auto(self):
        """Test auto-detection with mixed but parseable formats."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01T00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="mixed",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 00:00:00"
        assert result["DateTime"][1] == "2024-01-01 00:10:00"

    def test_12hour_to_24hour_format(self):
        """Test converting 12-hour to 24-hour format."""
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 02:30:00 PM", "2024-01-01 11:45:00 AM"],
            "WindSpeed": [5.2, 5.5]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %I:%M:%S %p",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result["DateTime"][0] == "2024-01-01 14:30:00"
        assert result["DateTime"][1] == "2024-01-01 11:45:00"

    def test_preserve_row_count(self):
        """Test that row count is preserved."""
        df = pl.DataFrame({
            "DateTime": [f"2024-01-01 {h:02d}:00:00" for h in range(24)],
            "WindSpeed": list(range(24))
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert len(result) == 24

    def test_column_order_preserved(self):
        """Test that column order is preserved."""
        df = pl.DataFrame({
            "Timestamp": ["2024-01-01 00:00:00"],
            "WindSpeed": [5.2],
            "DateTime": ["2024-01-01 00:00:00"],
            "Temperature": [15.3]
        })

        config = TimestampNormalizerConfig(
            input_path="test.csv",
            output_path="out.csv",
            timestamp_column="DateTime",
            input_format="%Y-%m-%d %H:%M:%S",
            output_format="%Y-%m-%d %H:%M:%S"
        )

        result = normalize_timestamp(df, config)

        assert result.columns == df.columns
