"""Recommend report configuration use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating report configuration files

This module provides the use case for generating report configuration
files based on fill-heights-representative-year data.
"""

from pathlib import Path

import polars as pl
import tomli
import tomli_w

from cleanmast.subdomains.reporting.value_objects.meta import calculate_air_density


def recommend_report(project_dir: str) -> Path:
    """Generate configuration for representative timeseries report.

    This use case:
    1. Reads fill-heights-representative-year.toml from the project directory
    2. For each mast, loads the parquet file from representative-year-fill-heights/
    3. Calculates air density from mean temperature/pressure columns
    4. Generates rep-ts-report.toml config file

    Prerequisites:
    - fill-heights-representative-year.toml must exist in project directory
    - Parquet files must exist in representative-year-fill-heights/ subdirectory

    Args:
        project_dir: Path to project directory containing config files

    Returns:
        Path to generated config file

    Raises:
        FileNotFoundError: If fill-heights config not found
        ValueError: If no masts found in config
    """
    project_path = Path(project_dir)

    # Load fill-heights-representative-year.toml
    fill_heights_path = project_path / "fill-heights-representative-year.toml"
    if not fill_heights_path.exists():
        raise FileNotFoundError(
            f"fill-heights-representative-year.toml not found at {fill_heights_path}. "
            "Run 'recommend fill-heights' command first."
        )

    with open(fill_heights_path, "rb") as f:
        fill_heights_config = tomli.load(f)

    # Extract mast configurations
    masts_config = fill_heights_config.get("masts", [])
    if not masts_config:
        raise ValueError(
            "No masts found in fill-heights-representative-year.toml"
        )

    # Process each mast
    report_masts = []
    for mast in masts_config:
        mast_name = mast.get("name")
        if not mast_name:
            continue

        # Get output path from fill-heights config (this is the filled data)
        output_config = mast.get("output", {})
        data_path = output_config.get("data", "")

        if not data_path:
            continue

        # Resolve parquet path (relative to project directory)
        parquet_path = project_path / data_path
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet file not found for mast {mast_name}: {parquet_path}"
            )

        # Load parquet and calculate air density
        try:
            df = pl.read_parquet(parquet_path)
            air_density = calculate_air_density(df)
        except Exception:
            air_density = 1.225  # Fallback to standard value

        # Build mast entry for report config
        # Convert to relative path for the config
        rel_data_path = f"./representative-year-fill-heights/{mast_name}.parquet"
        report_masts.append({
            "name": mast_name,
            "air_density": round(air_density, 3),
            "input": {
                "data": rel_data_path,
                # No sensors field - metadata is embedded in parquet
            },
        })

    if not report_masts:
        raise ValueError("No valid masts found for report configuration")

    # Generate report config
    report_config = {"masts": report_masts}

    # Write rep-ts-report.toml
    output_path = project_path / "rep-ts-report.toml"
    with open(output_path, "wb") as f:
        tomli_w.dump(report_config, f)

    return output_path
