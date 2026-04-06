"""Tests for type normalizer functionality."""

import tempfile
from pathlib import Path

import polars as pl
import pytest
from preprocess_tools.type_normalizer import (
    TypeNormalizerConfig,
    load_config,
    normalize_types,
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
        config_path = configs_dir / "type_normalizer.toml"
        config = load_config(str(config_path))

        assert isinstance(config, TypeNormalizerConfig)
        assert config.input_path == "../csv_files/wrong_types.csv"
        assert config.float_columns == ["WindSpeed", "WindDirection"]
        assert config.skip_rows == 0

    def test_load_nonexistent_config(self):
        """Test loading non-existent config file."""
        with pytest.raises(SystemExit):
            load_config("nonexistent.toml")


class TestTypeNormalization:
    """Tests for type normalization logic."""

    def test_normalize_string_to_float(self):
        """Test converting string columns to float."""
        df = pl.DataFrame({
            "Timestamp": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": ["5.2", "5.5"],
            "WindDirection": ["180.5", "182.3"]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection"])

        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Float64
        assert result["WindSpeed"][0] == 5.2
        assert result["WindDirection"][0] == 180.5

    def test_normalize_already_float(self):
        """Test that already-float columns remain unchanged."""
        df = pl.DataFrame({
            "WindSpeed": [5.2, 5.5],
            "WindDirection": [180.5, 182.3]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection"])

        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Float64

    def test_normalize_with_nulls(self):
        """Test converting strings with null values."""
        df = pl.DataFrame({
            "WindSpeed": ["5.2", "N/A", "6.1"],
            "WindDirection": ["180.5", "182.3", None]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection"])

        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindSpeed"][0] == 5.2
        assert result["WindSpeed"][1] is None

    def test_normalize_integer_to_float(self):
        """Test converting integer columns to float."""
        df = pl.DataFrame({
            "WindSpeed": [5, 6, 7],
            "WindDirection": [180, 182, 185]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection"])

        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Float64
        assert result["WindSpeed"][0] == 5.0

    def test_normalize_mixed_numeric_types(self):
        """Test converting mixed numeric type columns."""
        df = pl.DataFrame({
            "Value1": [1, 2, 3],
            "Value2": [1.5, 2.5, 3.5],
            "Value3": ["4.5", "5.5", "6.5"]
        })

        result = normalize_types(df, ["Value1", "Value2", "Value3"])

        assert result["Value1"].dtype == pl.Float64
        assert result["Value2"].dtype == pl.Float64
        assert result["Value3"].dtype == pl.Float64

    def test_normalize_nonexistent_column(self):
        """Test warning when specified column doesn't exist."""
        df = pl.DataFrame({
            "existing_col": ["1.0", "2.0"]
        })

        # Should not raise error, just skip the missing column
        result = normalize_types(df, ["existing_col", "nonexistent_col"])

        assert result["existing_col"].dtype == pl.Float64

    def test_normalize_partial_columns(self):
        """Test normalizing only some columns."""
        df = pl.DataFrame({
            "WindSpeed": ["5.2", "5.5"],
            "WindDirection": ["180.5", "182.3"],
            "Status": ["OK", "OK"]
        })

        result = normalize_types(df, ["WindSpeed"])

        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Utf8
        assert result["Status"].dtype == pl.Utf8

    def test_normalize_preserves_column_order(self):
        """Test that column order is preserved."""
        df = pl.DataFrame({
            "Timestamp": ["2024-01-01 00:00:00"],
            "WindSpeed": ["5.2"],
            "WindDirection": ["180.5"],
            "Temperature": ["15.3"]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection", "Temperature"])

        assert result.columns == df.columns


class TestFileProcessing:
    """Integration tests for file processing."""

    def test_process_complete_file(self, configs_dir, temp_output_dir):
        """Test processing a complete file with all steps."""
        config = load_config(str(configs_dir / "type_normalizer.toml"))
        config.output_path = str(temp_output_dir / "normalized.csv")

        process_file(config, configs_dir)

        output_file = Path(config.output_path)
        assert output_file.exists()

        result = pl.read_csv(output_file)
        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Float64
        assert result["Status"].dtype == pl.Utf8

    def test_process_nonexistent_file(self, configs_dir):
        """Test error when input file doesn't exist."""
        config = load_config(str(configs_dir / "type_normalizer.toml"))
        config.input_path = "nonexistent.csv"

        with pytest.raises(SystemExit):
            process_file(config, configs_dir)

    def test_process_tab_delimited(self, csv_files_dir, temp_output_dir):
        """Test processing tab-delimited file."""
        config = TypeNormalizerConfig(
            input_path=str(csv_files_dir / "tab_delimited.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            float_columns=["WindSpeed", "WindDirection", "Temperature"],
            delimiter="\t"
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert result["WindSpeed"].dtype == pl.Float64
        assert result["WindDirection"].dtype == pl.Float64
        assert result["Temperature"].dtype == pl.Float64

    def test_process_with_skip_rows(self, csv_files_dir, temp_output_dir):
        """Test processing file with skip_rows."""
        config = TypeNormalizerConfig(
            input_path=str(csv_files_dir / "with_header_rows.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            float_columns=["WindSpeed", "WindDirection", "Temperature"],
            skip_rows=3
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert result["WindSpeed"].dtype == pl.Float64
        assert len(result) == 3


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_float_columns_list(self):
        """Test with empty float_columns list."""
        df = pl.DataFrame({
            "col1": ["1", "2"],
            "col2": ["3", "4"]
        })

        result = normalize_types(df, [])

        # All columns should remain as strings
        assert result["col1"].dtype == pl.Utf8
        assert result["col2"].dtype == pl.Utf8

    def test_all_columns_to_float(self):
        """Test converting all columns to float."""
        df = pl.DataFrame({
            "col1": ["1.0", "2.0"],
            "col2": ["3.0", "4.0"],
            "col3": ["5.0", "6.0"]
        })

        result = normalize_types(df, ["col1", "col2", "col3"])

        assert all(result[col].dtype == pl.Float64 for col in result.columns)

    def test_single_row_dataframe(self):
        """Test with single row dataframe."""
        df = pl.DataFrame({
            "WindSpeed": ["5.2"],
            "WindDirection": ["180.5"]
        })

        result = normalize_types(df, ["WindSpeed", "WindDirection"])

        assert len(result) == 1
        assert result["WindSpeed"][0] == 5.2

    def test_large_numbers(self):
        """Test with large numbers."""
        df = pl.DataFrame({
            "LargeValue": ["1234567890.123456", "9876543210.654321"]
        })

        result = normalize_types(df, ["LargeValue"])

        assert result["LargeValue"].dtype == pl.Float64
        assert result["LargeValue"][0] == pytest.approx(1234567890.123456)

    def test_scientific_notation(self):
        """Test with scientific notation."""
        df = pl.DataFrame({
            "Scientific": ["1.23e-4", "5.67e8"]
        })

        result = normalize_types(df, ["Scientific"])

        assert result["Scientific"].dtype == pl.Float64
        assert result["Scientific"][0] == pytest.approx(1.23e-4)
        assert result["Scientific"][1] == pytest.approx(5.67e8)

    def test_negative_numbers(self):
        """Test with negative numbers."""
        df = pl.DataFrame({
            "Temperature": ["-15.3", "-10.2", "5.1"]
        })

        result = normalize_types(df, ["Temperature"])

        assert result["Temperature"].dtype == pl.Float64
        assert result["Temperature"][0] == -15.3

    def test_preserve_other_columns(self):
        """Test that non-converted columns are preserved."""
        df = pl.DataFrame({
            "Timestamp": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": ["5.2", "5.5"],
            "Status": ["OK", "ERROR"]
        })

        result = normalize_types(df, ["WindSpeed"])

        assert result["Timestamp"].dtype == pl.Utf8
        assert result["Status"].dtype == pl.Utf8
        assert result["Timestamp"][0] == "2024-01-01 00:00:00"
        assert result["Status"][0] == "OK"
