"""CSV merger for mast data files."""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional

import chardet
import click
import colorama
import polars as pl
import tomli
from pydantic import BaseModel, Field, ValidationError, model_validator


class DateTimeConfig(BaseModel):
    """Configuration for datetime parsing."""
    format: str = Field(..., description="Datetime format string")
    col: str = Field(..., description="Datetime column name")


class DateTimeConfigSeparate(BaseModel):
    """Configuration for separate date and time parsing."""
    date: DateTimeConfig = Field(..., description="Date configuration")
    time: DateTimeConfig = Field(..., description="Time configuration")


class HeadlineConfig(BaseModel):
    """Configuration for headline detection."""
    number: Optional[int] = Field(default=None, description="Header line number (0-based)")
    regex: Optional[str] = Field(default=None, description="Regex pattern to match header line")

    @model_validator(mode='after')
    def validate_headline_options(self):
        """Ensure exactly one of number or regex is provided."""
        if self.number is not None and self.regex is not None:
            raise ValueError("Cannot specify both 'number' and 'regex' for headline detection")
        if self.number is None and self.regex is None:
            raise ValueError("Must specify either 'number' or 'regex' for headline detection")
        return self


class InputConfig(BaseModel):
    """Configuration for input files."""
    dir: str = Field(..., description="Directory containing CSV files")
    datetime: Optional[DateTimeConfig] = Field(default=None, description="Single datetime column configuration")
    date: Optional[DateTimeConfig] = Field(default=None, description="Date column configuration")
    time: Optional[DateTimeConfig] = Field(default=None, description="Time column configuration")
    headline: HeadlineConfig = Field(..., description="Header detection configuration")
    delim: str = Field(default=",", description="Field delimiter")
    patterns: List[str] = Field(default=["*.csv"], description="File patterns to match (e.g., ['*.csv', '*.wnd'])")

    @model_validator(mode='after')
    def validate_datetime_options(self):
        """Ensure datetime options are correctly specified."""
        has_combined = self.datetime is not None
        has_separate = self.date is not None and self.time is not None

        if not has_combined and not has_separate:
            raise ValueError("Must specify either 'datetime' or both 'date' and 'time' configurations")
        if has_combined and has_separate:
            raise ValueError("Cannot specify both 'datetime' and separate 'date'/'time' configurations")
        if (self.date is None) != (self.time is None):
            raise ValueError("When using separate date/time, both 'date' and 'time' must be specified")

        return self


class CsvMergerConfig(BaseModel):
    """Configuration for CSV merger."""
    output: str = Field(..., description="Output file path relative to config.toml")
    input: InputConfig = Field(..., description="Input configuration")
    duplicate_handling: Optional[str] = Field(
        default='keep_last',
        description="How to handle duplicate timestamps: 'keep_first', 'keep_last', or None to keep all (default: 'keep_last')"
    )


def load_config(config_path: str) -> CsvMergerConfig:
    """Load and validate configuration from TOML file."""
    try:
        with open(config_path, "rb") as f:
            config_data = tomli.load(f)
        return CsvMergerConfig(**config_data)
    except FileNotFoundError:
        click.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
        sys.exit(1)
    except ValidationError as e:
        click.echo(f"Error: Invalid configuration: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to load configuration: {e}", err=True)
        sys.exit(1)


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']


def convert_to_utf8(file_path: str, detected_encoding: str) -> str:
    """Convert file to UTF-8 if needed and return temp file path."""
    if detected_encoding.lower() in ['utf-8', 'ascii']:
        return file_path

    # Log the conversion
    click.echo(f"Converting {Path(file_path).name}: {detected_encoding} -> UTF-8")

    # Read with detected encoding and write as UTF-8
    temp_path = file_path + '.utf8_temp'
    try:
        with open(file_path, 'r', encoding=detected_encoding) as infile:
            content = infile.read()
        with open(temp_path, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
        return temp_path
    except Exception as e:
        click.echo(f"Error converting {file_path} to UTF-8: {e}", err=True)
        return file_path


def find_header_line(file_path: str, headline_config: HeadlineConfig) -> int:
    """Find header line using either number or regex."""
    if headline_config.number is not None:
        return headline_config.number

    # Use regex to find header line
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            if re.search(headline_config.regex, line):
                return line_num

    raise ValueError(f"Header line not found using regex: {headline_config.regex}")


def read_csv_file(file_path: str, config: CsvMergerConfig) -> pl.DataFrame:
    """Read a single CSV file with proper encoding and header detection."""
    # Detect and convert encoding if needed
    detected_encoding = detect_encoding(file_path)
    utf8_file_path = convert_to_utf8(file_path, detected_encoding)

    try:
        # Find header line
        header_line = find_header_line(utf8_file_path, config.input.headline)

        # Read CSV with polars
        df = pl.read_csv(
            utf8_file_path,
            separator=config.input.delim,
            skip_rows=header_line,
            infer_schema_length=10000,
        )

        return df

    finally:
        # Clean up temp file if created
        if utf8_file_path != file_path and os.path.exists(utf8_file_path):
            os.remove(utf8_file_path)


def discover_csv_files(input_dir: str, config_dir: Path, patterns: List[str]) -> List[str]:
    """Discover all files matching the specified patterns in the input directory."""
    # Resolve input directory relative to config file
    if not Path(input_dir).is_absolute():
        input_path = config_dir / input_dir
    else:
        input_path = Path(input_dir)

    input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_path}")

    # Collect files matching any of the patterns
    files = []
    for pattern in patterns:
        files.extend(input_path.glob(pattern))

    if not files:
        raise ValueError(f"No files matching patterns {patterns} found in directory: {input_path}")

    return [str(f) for f in sorted(files)]


def validate_column_consistency(dataframes: List[pl.DataFrame], file_paths: List[str]) -> None:
    """Validate that all dataframes have identical column structures."""
    if not dataframes:
        return

    reference_columns = dataframes[0].columns

    for i, df in enumerate(dataframes[1:], 1):
        if df.columns != reference_columns:
            click.echo(f"Error: Column mismatch in file {Path(file_paths[i]).name}", err=True)
            click.echo(f"Expected columns: {reference_columns}", err=True)
            click.echo(f"Found columns: {df.columns}", err=True)
            sys.exit(1)


def create_timestamp_column(df: pl.DataFrame, config: CsvMergerConfig) -> pl.DataFrame:
    """Create a unified timestamp column for sorting and duplicate detection."""
    if config.input.datetime is not None:
        # Use single datetime column
        original_col = config.input.datetime.col

        # Parse datetime
        df = df.with_columns(
            pl.col(original_col).str.strptime(pl.Datetime, config.input.datetime.format).alias('_timestamp')
        )

        # Check if original column is already "Timestamp" with correct format
        if original_col == 'Timestamp':
            # Check if format is already correct
            sample_value = df['_timestamp'][0]
            original_value = df[original_col][0]
            formatted_sample = sample_value.strftime('%Y-%m-%d %H:%M:%S') if sample_value else None

            if str(original_value) == formatted_sample:
                # Case 1: Already correct format, keep original
                df = df.with_columns(pl.col(original_col).alias('Timestamp'))
            else:
                # Case 2: Wrong format, reformat and remove original
                df = df.with_columns(
                    pl.col('_timestamp').dt.strftime('%Y-%m-%d %H:%M:%S').alias('Timestamp')
                )
                df = df.drop(original_col)
        else:
            # Different column name, create new Timestamp and remove original
            df = df.with_columns(
                pl.col('_timestamp').dt.strftime('%Y-%m-%d %H:%M:%S').alias('Timestamp')
            )
            df = df.drop(original_col)
    else:
        # Combine date and time columns
        date_col_name = config.input.date.col
        time_col_name = config.input.time.col

        # Combine date and time strings
        combined_format = f"{config.input.date.format} {config.input.time.format}"
        df = df.with_columns(
            (pl.col(date_col_name).cast(pl.Utf8) + ' ' + pl.col(time_col_name).cast(pl.Utf8))
            .str.strptime(pl.Datetime, combined_format)
            .alias('_timestamp')
        )

        # Create standardized Timestamp column and remove original date/time columns
        df = df.with_columns(
            pl.col('_timestamp').dt.strftime('%Y-%m-%d %H:%M:%S').alias('Timestamp')
        )
        df = df.drop([date_col_name, time_col_name])

    return df


def check_and_handle_duplicates(df: pl.DataFrame, duplicate_handling: Optional[str] = None) -> pl.DataFrame:
    """Check for duplicate timestamps, warn, and optionally remove them.

    Args:
        df: DataFrame with '_timestamp' column
        duplicate_handling: One of 'keep_first', 'keep_last', or None
            - 'keep_first': Remove duplicate timestamps, keeping the first occurrence
            - 'keep_last': Remove duplicate timestamps, keeping the last occurrence
            - None: Keep all duplicates (default behavior)

    Returns:
        DataFrame with duplicates handled according to the specified strategy
    """
    # Find duplicates
    duplicates = df.filter(pl.col('_timestamp').is_duplicated())

    if len(duplicates) > 0:
        colorama.init()
        num_duplicate_timestamps = duplicates['_timestamp'].n_unique()
        num_duplicate_rows = len(duplicates)

        click.echo(
            f"{colorama.Fore.YELLOW}Warning: Found {num_duplicate_rows} duplicate rows "
            f"across {num_duplicate_timestamps} unique timestamps{colorama.Style.RESET_ALL}",
            err=True
        )

        unique_duplicate_timestamps = duplicates['_timestamp'].unique().sort()[:10].to_list()
        for timestamp in unique_duplicate_timestamps:
            click.echo(f"  Duplicate: {timestamp}", err=True)

        if num_duplicate_timestamps > 10:
            click.echo(f"  ... and {num_duplicate_timestamps - 10} more duplicate timestamps", err=True)

        if duplicate_handling == 'keep_first':
            click.echo(
                f"{colorama.Fore.CYAN}Removing duplicates: keeping first occurrence{colorama.Style.RESET_ALL}",
                err=True
            )
            df = df.unique(subset='_timestamp', keep='first')
        elif duplicate_handling == 'keep_last':
            click.echo(
                f"{colorama.Fore.CYAN}Removing duplicates: keeping last occurrence{colorama.Style.RESET_ALL}",
                err=True
            )
            df = df.unique(subset='_timestamp', keep='last')
        elif duplicate_handling is None:
            click.echo(
                f"{colorama.Fore.YELLOW}Keeping all duplicate rows. "
                f"Set 'duplicate_handling' in config to remove duplicates.{colorama.Style.RESET_ALL}",
                err=True
            )
        else:
            raise ValueError(
                f"Invalid duplicate_handling value: '{duplicate_handling}'. "
                f"Must be 'keep_first', 'keep_last', or None."
            )

    return df


def merge_csv_files(config: CsvMergerConfig, config_dir: Path) -> pl.DataFrame:
    """Main function to merge CSV files."""
    # Initialize colorama for colored output
    colorama.init()

    # Discover files matching patterns
    csv_files = discover_csv_files(config.input.dir, config_dir, config.input.patterns)
    click.echo(f"Found {len(csv_files)} files to merge")

    # Read all CSV files
    dataframes = []
    for file_path in csv_files:
        click.echo(f"Processing: {Path(file_path).name}")
        df = read_csv_file(file_path, config)
        df = create_timestamp_column(df, config)
        dataframes.append(df)

    # Validate column consistency
    validate_column_consistency(dataframes, csv_files)

    # Merge all dataframes
    merged_df = pl.concat(dataframes)

    # Sort by timestamp
    merged_df = merged_df.sort('_timestamp')

    # Check and handle duplicates
    merged_df = check_and_handle_duplicates(merged_df, config.duplicate_handling)

    # Remove temporary timestamp column and reorder columns to put Timestamp first
    merged_df = merged_df.drop('_timestamp')

    # Reorder columns to put Timestamp first
    other_columns = [col for col in merged_df.columns if col != 'Timestamp']
    merged_df = merged_df.select(['Timestamp'] + other_columns)

    return merged_df


@click.command()
@click.argument('config_path', type=click.Path(exists=True))
def main(config_path: str) -> None:
    """Merge multiple CSV files based on configuration."""
    config = load_config(config_path)

    # Get config directory for resolving relative paths
    config_dir = Path(config_path).parent

    # Resolve output path relative to config file
    if not Path(config.output).is_absolute():
        output_path = config_dir / config.output
    else:
        output_path = Path(config.output)

    output_path = output_path.resolve()

    try:
        # Merge CSV files
        merged_df = merge_csv_files(config, config_dir)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged_df.write_csv(output_path)

        click.echo(f"Successfully merged {len(merged_df)} rows to: {output_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
