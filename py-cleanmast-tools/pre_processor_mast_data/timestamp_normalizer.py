"""Timestamp normalizer for mast data files."""

import sys
from pathlib import Path
from typing import Optional

import click
import pandas as pd
import tomli
from pydantic import BaseModel, Field, ValidationError


class TimestampNormalizerConfig(BaseModel):
    """Configuration for timestamp normalizer."""

    input_path: str = Field(..., description="Path to input CSV/DAT file")
    output_path: str = Field(..., description="Path to output CSV file")
    timestamp_column: str = Field(..., description="Name of the timestamp column to normalize")
    input_format: str = Field(..., description="Input timestamp format ('mixed', 'auto', or strftime format)")
    output_format: Optional[str] = Field(default="%Y-%m-%d %H:%M:%S", description="Output timestamp format")
    skip_rows: Optional[int] = Field(default=0, description="Number of rows to skip at the beginning")
    header_row: Optional[int] = Field(default=0, description="Row number containing headers (0-based)")
    delimiter: Optional[str] = Field(default=",", description="Field delimiter (e.g., ',' for CSV, '\\t' for TSV)")


def load_config(config_path: str) -> TimestampNormalizerConfig:
    """Load and validate configuration from TOML file."""
    try:
        with open(config_path, "rb") as f:
            config_data = tomli.load(f)
        return TimestampNormalizerConfig(**config_data)
    except FileNotFoundError:
        click.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
        sys.exit(1)
    except ValidationError as e:
        click.echo(f"Error: Invalid configuration: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to load configuration: {e}", err=True)
        sys.exit(1)


def normalize_timestamp(df: pd.DataFrame, config: TimestampNormalizerConfig) -> pd.DataFrame:
    """Normalize timestamp column to proper format."""
    df_converted = df.copy()
    
    if config.timestamp_column not in df_converted.columns:
        click.echo(f"Error: Timestamp column '{config.timestamp_column}' not found in data.", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"Converting timestamp column '{config.timestamp_column}'")
        click.echo(f"  Input format: {config.input_format}")
        click.echo(f"  Output format: {config.output_format}")
        
        # Parse the timestamp using the input format
        if config.input_format == "mixed":
            # Let pandas infer the format automatically for each element
            df_converted[config.timestamp_column] = pd.to_datetime(
                df_converted[config.timestamp_column], 
                format="mixed"
            )
        elif config.input_format == "auto":
            # Let pandas auto-detect the format
            df_converted[config.timestamp_column] = pd.to_datetime(
                df_converted[config.timestamp_column]
            )
        else:
            # Use the specified format
            df_converted[config.timestamp_column] = pd.to_datetime(
                df_converted[config.timestamp_column], 
                format=config.input_format
            )
        
        # Format to output format
        output_format = config.output_format or "%Y-%m-%d %H:%M:%S"
        df_converted[config.timestamp_column] = df_converted[config.timestamp_column].dt.strftime(
            output_format
        )
        
        click.echo(f"Successfully converted timestamp column")
        click.echo(f"Sample converted timestamps:")
        click.echo(f"  {df_converted[config.timestamp_column].head(3).tolist()}")
        
    except Exception as e:
        click.echo(f"Error: Failed to convert timestamp: {e}", err=True)
        sys.exit(1)
    
    return df_converted


def process_file(config: TimestampNormalizerConfig, config_dir: Path) -> None:
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
            df = pd.read_csv(
                input_path,
                skiprows=config.skip_rows,
                header=config.header_row,
                index_col=False,  # Prevent pandas from using first column as index
                sep=config.delimiter
            )
        else:
            click.echo(f"Error: Unsupported file format '{input_path.suffix}'", err=True)
            sys.exit(1)
        
        click.echo(f"Loaded {len(df)} rows and {len(df.columns)} columns")
        
        # Normalize timestamp
        df_normalized = normalize_timestamp(df, config)
        
        # Save the normalized data
        click.echo(f"Saving normalized data to: {output_path}")
        df_normalized.to_csv(output_path, index=False)
        
        click.echo("Timestamp normalization completed successfully!")
        
    except Exception as e:
        click.echo(f"Error: Failed to process file: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument('config_path', type=click.Path(exists=True))
def main(config_path: str) -> None:
    """
    Normalize timestamps in mast data files based on TOML configuration.

    CONFIG_PATH: Path to the TOML configuration file
    """
    click.echo("Timestamp Normalizer for Mast Data")
    click.echo("=" * 35)

    config_file_path = Path(config_path)
    config_dir = config_file_path.parent

    config = load_config(config_path)
    process_file(config, config_dir)


if __name__ == "__main__":
    main()
