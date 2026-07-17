"""Type normalizer for mast data files."""

import sys
from pathlib import Path
from typing import List, Optional, Union

import click
import polars as pl
import tomli
from pydantic import BaseModel, Field, ValidationError


class TypeNormalizerConfig(BaseModel):
    """Configuration for type normalizer."""

    input_path: str = Field(..., description="Path to input CSV/DAT file")
    output_path: str = Field(..., description="Path to output CSV file")
    float_columns: List[str] = Field(..., description="List of column names to convert to float")
    skip_rows: Optional[Union[int, List[int]]] = Field(default=0, description="Number of rows to skip at the beginning or list of row indices to skip")
    header_row: Optional[int] = Field(default=0, description="Row number containing headers (0-based)")
    delimiter: Optional[str] = Field(default=",", description="Field delimiter (e.g., ',' for CSV, '\\t' for TSV)")


def load_config(config_path: str) -> TypeNormalizerConfig:
    """Load and validate configuration from TOML file."""
    try:
        with open(config_path, "rb") as f:
            config_data = tomli.load(f)
        return TypeNormalizerConfig(**config_data)
    except FileNotFoundError:
        click.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
        sys.exit(1)
    except ValidationError as e:
        click.echo(f"Error: Invalid configuration: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to load configuration: {e}", err=True)
        sys.exit(1)


def normalize_types(df: pl.DataFrame, float_columns: List[str]) -> pl.DataFrame:
    """Normalize column types by converting specified columns to float."""
    # Show original types for columns that will be converted
    for col in float_columns:
        if col not in df.columns:
            click.echo(f"Warning: Column '{col}' not found in data. Skipping.", err=True)
            continue

        original_type = df[col].dtype
        click.echo(f"Converting column '{col}' from {original_type} to Float64")

    # Convert specified columns to Float64, handling non-numeric values
    return df.with_columns([
        pl.col(col).cast(pl.Float64, strict=False)
        for col in float_columns
        if col in df.columns
    ])


def process_file(config: TypeNormalizerConfig, config_dir: Path) -> None:
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
            # Calculate skip_rows for polars
            # Polars skip_rows skips N rows before reading the header; it does not
            # accept a list of row indices, so narrow the config union to int.
            skip_rows_param = config.skip_rows if isinstance(config.skip_rows, int) else 0
            click.echo(f"DEBUG: skip_rows_param = {skip_rows_param}")
            click.echo(f"DEBUG: header_row = {config.header_row}")

            df = pl.read_csv(
                input_path,
                skip_rows=skip_rows_param,
                separator=config.delimiter or ",",
                infer_schema_length=10000,  # Infer types from more rows
            )

            # Debug: show first few rows
            click.echo("DEBUG: First 3 rows of loaded DataFrame:")
            click.echo(df.head(3))
        else:
            click.echo(f"Error: Unsupported file format '{input_path.suffix}'", err=True)
            sys.exit(1)

        click.echo(f"Loaded {len(df)} rows and {len(df.columns)} columns")

        # Normalize types
        df_normalized = normalize_types(df, config.float_columns)

        # Save the normalized data
        click.echo(f"Saving normalized data to: {output_path}")
        df_normalized.write_csv(output_path)

        click.echo("Type normalization completed successfully!")

        # Show summary of changes
        click.echo("\nSummary:")
        for col in config.float_columns:
            if col in df.columns:
                original_type = df[col].dtype
                new_type = df_normalized[col].dtype
                click.echo(f"  {col}: {original_type} -> {new_type}")

    except Exception as e:
        click.echo(f"Error: Failed to process file: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument('config_path', type=click.Path(exists=True))
def main(config_path: str) -> None:
    """
    Normalize data types in mast data files based on TOML configuration.

    CONFIG_PATH: Path to the TOML configuration file
    """
    click.echo("Type Normalizer for Mast Data")
    click.echo("=" * 30)

    config_file_path = Path(config_path)
    config_dir = config_file_path.parent

    config = load_config(config_path)
    process_file(config, config_dir)


if __name__ == "__main__":
    main()
