"""Tests for column name normalizer functionality."""

import tempfile
from pathlib import Path

import polars as pl
import pytest
from preprocess_tools.col_name_normalizer import (
    ColNameNormalizerConfig,
    load_config,
    normalize_column_names,
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
        config_path = configs_dir / "col_normalizer.toml"
        config = load_config(str(config_path))

        assert isinstance(config, ColNameNormalizerConfig)
        assert config.input_path == "../csv_files/different_columns.csv"
        assert config.keep_unmapped is True
        assert len(config.column_mappings) == 4

    def test_load_nonexistent_config(self):
        """Test loading non-existent config file."""
        with pytest.raises(SystemExit):
            load_config("nonexistent.toml")


class TestColumnNormalization:
    """Tests for column name normalization logic."""

    def test_normalize_basic_mapping(self):
        """Test basic column name mapping."""
        df = pl.DataFrame({
            "old_name1": [1, 2, 3],
            "old_name2": [4, 5, 6]
        })

        mappings = {
            "old_name1": "new_name1",
            "old_name2": "new_name2"
        }

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert "new_name1" in result.columns
        assert "new_name2" in result.columns
        assert "old_name1" not in result.columns
        assert "old_name2" not in result.columns

    def test_normalize_with_unmapped_columns(self):
        """Test normalization keeping unmapped columns."""
        df = pl.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9]
        })

        mappings = {"col1": "new_col1"}

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert "new_col1" in result.columns
        assert "col2" in result.columns
        assert "col3" in result.columns
        assert len(result.columns) == 3

    def test_normalize_drop_unmapped_columns(self):
        """Test normalization dropping unmapped columns."""
        df = pl.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9]
        })

        mappings = {"col1": "new_col1"}

        result = normalize_column_names(df, mappings, keep_unmapped=False)

        assert "new_col1" in result.columns
        assert "col2" in result.columns
        assert "col3" in result.columns

    def test_normalize_missing_source_columns(self):
        """Test normalization when source columns don't exist."""
        df = pl.DataFrame({
            "existing_col": [1, 2, 3]
        })

        mappings = {
            "nonexistent_col": "new_name",
            "existing_col": "renamed_col"
        }

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert "renamed_col" in result.columns
        assert "nonexistent_col" not in result.columns
        assert "new_name" not in result.columns

    def test_normalize_timestamp_first(self):
        """Test that Timestamp column is moved to first position."""
        df = pl.DataFrame({
            "WindSpeed": [5.2, 5.5],
            "time_stamp": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindDirection": [180.5, 182.3]
        })

        mappings = {"time_stamp": "Timestamp"}

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert result.columns[0] == "Timestamp"

    def test_normalize_various_timestamp_names(self):
        """Test detection of various timestamp column names."""
        for ts_name in ["Timestamp", "TimeStamp", "timestamp", "TIMESTAMP"]:
            df = pl.DataFrame({
                "WindSpeed": [5.2],
                "OtherCol": [1],
                ts_name: ["2024-01-01 00:00:00"]
            })

            result = normalize_column_names(df, {}, keep_unmapped=True)
            assert result.columns[0] == ts_name


class TestFileProcessing:
    """Integration tests for file processing."""

    def test_process_complete_file(self, configs_dir, temp_output_dir):
        """Test processing a complete file with all steps."""
        config = load_config(str(configs_dir / "col_normalizer.toml"))
        config.output_path = str(temp_output_dir / "normalized.csv")

        process_file(config, configs_dir)

        output_file = Path(config.output_path)
        assert output_file.exists()

        result = pl.read_csv(output_file)
        assert "Timestamp" in result.columns
        assert "WindSpeed_80m" in result.columns
        assert "WindDirection_80m" in result.columns
        assert "Temperature" in result.columns

    def test_process_nonexistent_file(self, configs_dir):
        """Test error when input file doesn't exist."""
        config = load_config(str(configs_dir / "col_normalizer.toml"))
        config.input_path = "nonexistent.csv"

        with pytest.raises(SystemExit):
            process_file(config, configs_dir)

    def test_process_tab_delimited(self, csv_files_dir, temp_output_dir):
        """Test processing tab-delimited file."""
        config = ColNameNormalizerConfig(
            input_path=str(csv_files_dir / "tab_delimited.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            column_mappings={"WindSpeed": "WS", "WindDirection": "WD"},
            delimiter="\t",
            keep_unmapped=True
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert "WS" in result.columns
        assert "WD" in result.columns

    def test_process_with_skip_rows(self, csv_files_dir, temp_output_dir):
        """Test processing file with skip_rows."""
        config = ColNameNormalizerConfig(
            input_path=str(csv_files_dir / "with_header_rows.csv"),
            output_path=str(temp_output_dir / "output.csv"),
            column_mappings={"WindSpeed": "WS"},
            skip_rows=3,
            keep_unmapped=True
        )

        process_file(config, csv_files_dir.parent)

        result = pl.read_csv(temp_output_dir / "output.csv")
        assert "WS" in result.columns
        assert len(result) == 3


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_mappings(self):
        """Test with no column mappings."""
        df = pl.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6]
        })

        result = normalize_column_names(df, {}, keep_unmapped=True)

        assert len(result.columns) == 2
        assert "col1" in result.columns

    def test_duplicate_target_names(self):
        """Test handling of duplicate target column names."""
        df = pl.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6]
        })

        mappings = {
            "col1": "same_name",
            "col2": "same_name"
        }

        # This should raise a DuplicateError since polars doesn't allow duplicate column names
        with pytest.raises(pl.exceptions.DuplicateError):
            normalize_column_names(df, mappings, keep_unmapped=True)

    def test_single_column_dataframe(self):
        """Test with single column dataframe."""
        df = pl.DataFrame({"only_col": [1, 2, 3]})

        mappings = {"only_col": "renamed"}

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert len(result.columns) == 1
        assert "renamed" in result.columns

    def test_preserve_data_values(self):
        """Test that data values are preserved after normalization."""
        df = pl.DataFrame({
            "old_name": [1.5, 2.7, 3.9],
            "keep_name": ["a", "b", "c"]
        })

        mappings = {"old_name": "new_name"}

        result = normalize_column_names(df, mappings, keep_unmapped=True)

        assert result["new_name"].to_list() == [1.5, 2.7, 3.9]
        assert result["keep_name"].to_list() == ["a", "b", "c"]
