"""Column name normalizer for mast data files."""

import sys
from pathlib import Path
from typing import Dict, Optional

import click
import polars as pl
import tomli
from pydantic import BaseModel, Field, ValidationError, model_validator


TIMESTAMP_NAMES = {"Timestamp", "TimeStamp", "timestamp", "TIMESTAMP"}


class ColNameNormalizerConfig(BaseModel):
    """Configuration for column name normalizer."""

    input_path: str = Field(..., description="Path to input CSV/DAT file")
    output_path: str = Field(..., description="Path to output CSV file")
    column_mappings: Dict[str, str] = Field(..., description="Dictionary mapping old column names to new column names")
    skip_rows: Optional[int] = Field(default=0, description="Number of rows to skip at the beginning")
    header_row: Optional[int] = Field(default=0, description="Row number containing headers (0-based)")
    keep_unmapped: Optional[bool] = Field(default=True, description="Whether to keep columns not in mapping")
    delimiter: Optional[str] = Field(default=",", description="Field delimiter (e.g., ',' for CSV, '\\t' for TSV)")

    @model_validator(mode="after")
    def reject_timestamp_in_mappings(self):
        """Timestamp handling is reserved for csv-merger; forbid it in column_mappings."""
        for old_name, new_name in self.column_mappings.items():
            if old_name in TIMESTAMP_NAMES:
                raise ValueError(
                    f"column_mappings must not contain timestamp column '{old_name}'. "
                    f"Use csv-merger to create the Timestamp column, then col-normalizer "
                    f"will auto-preserve it."
                )
            if new_name in TIMESTAMP_NAMES:
                raise ValueError(
                    f"column_mappings must not map to timestamp column name '{new_name}'. "
                    f"Use csv-merger to create the Timestamp column, then col-normalizer "
                    f"will auto-preserve it."
                )
        return self


def load_config(config_path: str) -> ColNameNormalizerConfig:
    """Load and validate configuration from TOML file."""
    try:
        with open(config_path, "rb") as f:
            config_data = tomli.load(f)
        return ColNameNormalizerConfig(**config_data)
    except FileNotFoundError:
        click.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
        sys.exit(1)
    except ValidationError as e:
        click.echo(f"Error: Invalid configuration: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to load configuration: {e}", err=True)
        sys.exit(1)



def normalize_column_names(df: pl.DataFrame, column_mappings: Dict[str, str], keep_unmapped: bool = True) -> pl.DataFrame:
    """Normalize column names according to the mapping."""
    # Track which columns were renamed
    renamed_columns = {}
    missing_columns = []

    for old_name, new_name in column_mappings.items():
        if old_name in df.columns:
            renamed_columns[old_name] = new_name
        else:
            missing_columns.append(old_name)

    # Apply the renaming
    df_normalized = df.rename(renamed_columns)

    # Report results
    if renamed_columns:
        click.echo(f"Renamed {len(renamed_columns)} columns:")
        for old_name, new_name in renamed_columns.items():
            click.echo(f"  '{old_name}' -> '{new_name}'")

    if missing_columns:
        click.echo(f"Warning: {len(missing_columns)} columns from mapping not found in data:")
        for col in missing_columns:
            click.echo(f"  '{col}'")

    if not keep_unmapped:
        mapped_new_names = set(renamed_columns.values())
        preserved = {c for c in df_normalized.columns if c in TIMESTAMP_NAMES}
        columns_to_keep = list(mapped_new_names | preserved)
        df_normalized = df_normalized.select(columns_to_keep)
        click.echo(f"Kept {len(columns_to_keep)} columns (removed unmapped columns)")

    timestamp_col = None
    for ts_name in TIMESTAMP_NAMES:
        if ts_name in df_normalized.columns:
            timestamp_col = ts_name
            break

    if timestamp_col:
        cols = df_normalized.columns
        other_cols = [c for c in cols if c != timestamp_col]
        df_normalized = df_normalized.select([timestamp_col] + other_cols)
        click.echo(f"Moved '{timestamp_col}' column to first position")

    return df_normalized


def process_file(config: ColNameNormalizerConfig, config_dir: Path) -> None:
    """Process the input file according to configuration."""
    # Resolve paths relative to config file directory
    input_path = config_dir / config.input_path
    output_path = config_dir / config.output_path

    if not input_path.exists():
        click.echo(f"Error: Input file '{input_path}' not found.", err=True)
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Read the input file
        click.echo(f"Reading input file: {input_path}")

        # Handle different file formats
        if input_path.suffix.lower() in ['.csv', '.dat', '.txt']:
            df = pl.read_csv(
                input_path,
                skip_rows=config.skip_rows if config.skip_rows else 0,
                separator=config.delimiter or ",",
                infer_schema_length=10000,
            )
        else:
            click.echo(f"Error: Unsupported file format '{input_path.suffix}'", err=True)
            sys.exit(1)

        click.echo(f"Loaded {len(df)} rows and {len(df.columns)} columns")
        click.echo(f"Original columns: {df.columns}")

        # Normalize column names
        keep_unmapped = config.keep_unmapped if config.keep_unmapped is not None else True
        df_normalized = normalize_column_names(df, config.column_mappings, keep_unmapped)

        # Save the normalized data
        click.echo(f"Saving normalized data to: {output_path}")
        df_normalized.write_csv(output_path)

        click.echo("Column name normalization completed successfully!")

        # Show final column names
        click.echo(f"\nFinal columns: {df_normalized.columns}")

    except Exception as e:
        click.echo(f"Error: Failed to process file: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument('config_path', type=click.Path(exists=True))
def main(config_path: str) -> None:
    """
    Normalize column names in mast data files based on TOML configuration.

    CONFIG_PATH: Path to the TOML configuration file
    """
    click.echo("Column Name Normalizer for Mast Data")
    click.echo("=" * 35)

    config_file_path = Path(config_path)
    config_dir = config_file_path.parent

    config = load_config(config_path)
    process_file(config, config_dir)


if __name__ == "__main__":
    main()
