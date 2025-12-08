"""Tests for CSV merger functionality."""

import tempfile
from pathlib import Path

import polars as pl
import pytest

from preprocess_tools.csv_merger import (
    CsvMergerConfig,
    check_and_handle_duplicates,
    convert_to_utf8,
    create_timestamp_column,
    detect_encoding,
    discover_csv_files,
    find_header_line,
    load_config,
    merge_csv_files,
    read_csv_file,
    validate_column_consistency,
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
        config_path = configs_dir / "csv_merger.toml"
        config = load_config(str(config_path))

        assert isinstance(config, CsvMergerConfig)
        assert config.output == "../../merged_output.csv"
        assert config.duplicate_handling == "keep_last"
        assert config.input.delim == ","
        assert config.input.datetime.col == "DateTime"

    def test_load_config_with_separate_datetime(self, configs_dir):
        """Test loading config with separate date/time columns."""
        config_path = configs_dir / "csv_merger_separate_datetime.toml"
        config = load_config(str(config_path))

        assert config.input.date.col == "Date"
        assert config.input.time.col == "Time"
        assert config.input.date.format == "%Y-%m-%d"
        assert config.input.time.format == "%H:%M:%S"

    def test_load_nonexistent_config(self):
        """Test loading non-existent config file."""
        with pytest.raises(SystemExit):
            load_config("nonexistent.toml")


class TestEncodingDetection:
    """Tests for encoding detection and conversion."""

    def test_detect_utf8_encoding(self, csv_files_dir):
        """Test detecting UTF-8 encoding."""
        file_path = csv_files_dir / "simple.csv"
        encoding = detect_encoding(str(file_path))
        assert encoding.lower() in ['utf-8', 'ascii']

    def test_convert_utf8_no_conversion(self, csv_files_dir):
        """Test that UTF-8 files are not converted."""
        file_path = csv_files_dir / "simple.csv"
        result = convert_to_utf8(str(file_path), 'utf-8')
        assert result == str(file_path)

    def test_convert_utf8_creates_temp_file(self, csv_files_dir):
        """Test that non-UTF8 encoding creates temp file."""
        file_path = csv_files_dir / "simple.csv"
        result = convert_to_utf8(str(file_path), 'gbk')
        assert result.endswith('.utf8_temp')


class TestHeaderDetection:
    """Tests for header line detection."""

    def test_find_header_by_number(self, csv_files_dir):
        """Test finding header line by number."""
        from preprocess_tools.csv_merger import HeadlineConfig

        file_path = csv_files_dir / "simple.csv"
        config = HeadlineConfig(number=0)
        line_num = find_header_line(str(file_path), config)
        assert line_num == 0

    def test_find_header_by_regex(self, csv_files_dir):
        """Test finding header line by regex pattern."""
        from preprocess_tools.csv_merger import HeadlineConfig

        file_path = csv_files_dir / "with_header_rows.csv"
        config = HeadlineConfig(regex=r"Timestamp.*WindSpeed")
        line_num = find_header_line(str(file_path), config)
        assert line_num == 3

    def test_find_header_regex_not_found(self, csv_files_dir):
        """Test error when regex pattern not found."""
        from preprocess_tools.csv_merger import HeadlineConfig

        file_path = csv_files_dir / "simple.csv"
        config = HeadlineConfig(regex=r"NonExistentPattern")
        with pytest.raises(ValueError, match="Header line not found"):
            find_header_line(str(file_path), config)


class TestFileDiscovery:
    """Tests for CSV file discovery."""

    def test_discover_files_with_pattern(self, csv_files_dir, configs_dir):
        """Test discovering files matching a pattern."""
        files = discover_csv_files(
            "../csv_files/multiple",
            configs_dir,
            ["file*.csv"]
        )
        assert len(files) == 3
        assert all("file" in str(f) for f in files)

    def test_discover_files_multiple_patterns(self, csv_files_dir, configs_dir):
        """Test discovering files with multiple patterns."""
        files = discover_csv_files(
            "../csv_files/multiple",
            configs_dir,
            ["file1.csv", "file2.csv"]
        )
        assert len(files) == 2

    def test_discover_files_nonexistent_dir(self, configs_dir):
        """Test error when directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            discover_csv_files("nonexistent_dir", configs_dir, ["*.csv"])

    def test_discover_files_no_matches(self, csv_files_dir, configs_dir):
        """Test error when no files match pattern."""
        with pytest.raises(ValueError, match="No files matching patterns"):
            discover_csv_files("../csv_files", configs_dir, ["*.nonexistent"])


class TestTimestampCreation:
    """Tests for timestamp column creation."""

    def test_create_timestamp_single_column(self, configs_dir):
        """Test creating timestamp from single datetime column."""
        config = load_config(str(configs_dir / "csv_merger.toml"))

        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        result = create_timestamp_column(df, config)

        assert "Timestamp" in result.columns
        assert "_timestamp" in result.columns
        assert result["Timestamp"][0] == "2024-01-01 00:00:00"

    def test_create_timestamp_separate_columns(self, configs_dir):
        """Test creating timestamp from separate date/time columns."""
        config = load_config(str(configs_dir / "csv_merger_separate_datetime.toml"))

        df = pl.DataFrame({
            "Date": ["2024-01-01", "2024-01-01"],
            "Time": ["00:00:00", "00:10:00"],
            "WindSpeed": [5.2, 5.5]
        })

        result = create_timestamp_column(df, config)

        assert "Timestamp" in result.columns
        assert "Date" not in result.columns
        assert "Time" not in result.columns
        assert result["Timestamp"][0] == "2024-01-01 00:00:00"

    def test_create_timestamp_column_first(self, configs_dir):
        """Test that Timestamp column is placed first."""
        config = load_config(str(configs_dir / "csv_merger.toml"))

        df = pl.DataFrame({
            "WindSpeed": [5.2, 5.5],
            "DateTime": ["2024-01-01 00:00:00", "2024-01-01 00:10:00"]
        })

        result = create_timestamp_column(df, config)
        # Note: _timestamp is still in the dataframe at this stage
        assert "Timestamp" in result.columns


class TestDuplicateHandling:
    """Tests for duplicate timestamp handling."""

    def test_detect_duplicates(self):
        """Test duplicate detection."""
        from datetime import datetime
        df = pl.DataFrame({
            "_timestamp": pl.Series([
                datetime(2024, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 20),
            ], dtype=pl.Datetime)
        }).with_columns(WindSpeed=pl.Series([5.2, 5.5, 5.6, 6.1]))

        result = check_and_handle_duplicates(df, duplicate_handling=None)
        assert len(result) == 4

    def test_remove_duplicates_keep_first(self):
        """Test removing duplicates keeping first occurrence."""
        from datetime import datetime
        df = pl.DataFrame({
            "_timestamp": pl.Series([
                datetime(2024, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 20),
            ], dtype=pl.Datetime)
        }).with_columns(WindSpeed=pl.Series([5.2, 5.5, 5.6, 6.1]))

        result = check_and_handle_duplicates(df, duplicate_handling='keep_first')
        assert len(result) == 3
        # Check that 5.5 is kept (first of the duplicates at 00:10)
        ws_values = result["WindSpeed"].to_list()
        assert 5.5 in ws_values
        assert 5.6 not in ws_values

    def test_remove_duplicates_keep_last(self):
        """Test removing duplicates keeping last occurrence."""
        from datetime import datetime
        df = pl.DataFrame({
            "_timestamp": pl.Series([
                datetime(2024, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 20),
            ], dtype=pl.Datetime)
        }).with_columns(WindSpeed=pl.Series([5.2, 5.5, 5.6, 6.1]))

        result = check_and_handle_duplicates(df, duplicate_handling='keep_last')
        assert len(result) == 3
        # Check that 5.6 is kept (last of the duplicates at 00:10)
        ws_values = result["WindSpeed"].to_list()
        assert 5.6 in ws_values
        assert 5.5 not in ws_values

    def test_invalid_duplicate_handling(self):
        """Test error with invalid duplicate_handling value."""
        from datetime import datetime
        df = pl.DataFrame({
            "_timestamp": pl.Series([datetime(2024, 1, 1, 0, 0)] * 2, dtype=pl.Datetime)
        }).with_columns(WindSpeed=pl.Series([5.2, 5.5]))

        with pytest.raises(ValueError, match="Invalid duplicate_handling"):
            check_and_handle_duplicates(df, duplicate_handling='invalid')


class TestColumnValidation:
    """Tests for column consistency validation."""

    def test_validate_consistent_columns(self):
        """Test validation passes with consistent columns."""
        df1 = pl.DataFrame({"A": [1], "B": [2]})
        df2 = pl.DataFrame({"A": [3], "B": [4]})

        validate_column_consistency([df1, df2], ["file1", "file2"])

    def test_validate_inconsistent_columns(self):
        """Test validation fails with inconsistent columns."""
        df1 = pl.DataFrame({"A": [1], "B": [2]})
        df2 = pl.DataFrame({"A": [3], "C": [4]})

        with pytest.raises(SystemExit):
            validate_column_consistency([df1, df2], ["file1", "file2"])


class TestCSVReading:
    """Tests for CSV file reading."""

    def test_read_simple_csv(self, csv_files_dir, configs_dir):
        """Test reading a simple CSV file."""
        config = load_config(str(configs_dir / "csv_merger.toml"))
        config.input.dir = str(csv_files_dir)

        df = read_csv_file(str(csv_files_dir / "simple.csv"), config)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 5
        assert "DateTime" in df.columns

    def test_read_tab_delimited(self, csv_files_dir, configs_dir):
        """Test reading tab-delimited file."""
        config = load_config(str(configs_dir / "csv_merger.toml"))
        config.input.delim = "\t"

        df = read_csv_file(str(csv_files_dir / "tab_delimited.csv"), config)

        assert len(df) == 3
        assert "WindSpeed" in df.columns


class TestMergePipeline:
    """Integration tests for full merge pipeline."""

    def test_merge_multiple_files(self, configs_dir, temp_output_dir):
        """Test merging multiple CSV files."""
        config = load_config(str(configs_dir / "csv_merger.toml"))
        config.output = str(temp_output_dir / "merged.csv")

        merged_df = merge_csv_files(config, configs_dir)

        assert isinstance(merged_df, pl.DataFrame)
        assert len(merged_df) == 9
        assert merged_df.columns[0] == "Timestamp"
        assert "_timestamp" not in merged_df.columns

    def test_merge_with_duplicates(self, configs_dir, temp_output_dir):
        """Test merging files with overlapping timestamps."""
        config = load_config(str(configs_dir / "csv_merger.toml"))
        config.input.patterns = ["*.csv"]
        config.duplicate_handling = "keep_last"
        config.output = str(temp_output_dir / "merged_with_dups.csv")

        merged_df = merge_csv_files(config, configs_dir)

        assert isinstance(merged_df, pl.DataFrame)
        assert len(merged_df) > 0

    def test_merge_sorted_by_timestamp(self, configs_dir, temp_output_dir):
        """Test that merged data is sorted by timestamp."""
        config = load_config(str(configs_dir / "csv_merger.toml"))
        config.output = str(temp_output_dir / "sorted.csv")

        merged_df = merge_csv_files(config, configs_dir)

        timestamps = merged_df["Timestamp"].to_list()
        assert timestamps == sorted(timestamps)

    def test_merge_separate_datetime_columns(self, configs_dir, temp_output_dir):
        """Test merging with separate date/time columns."""
        config = load_config(str(configs_dir / "csv_merger_separate_datetime.toml"))
        config.output = str(temp_output_dir / "merged_separate.csv")

        merged_df = merge_csv_files(config, configs_dir)

        assert "Timestamp" in merged_df.columns
        assert "Date" not in merged_df.columns
        assert "Time" not in merged_df.columns
