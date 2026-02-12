"""CLI commands for fill-heights functionality.

This module provides Click-based CLI commands for the fill-heights system.

Commands:
=========

1. recommend fill-heights:
   - Generates fill-heights configuration files
   - Fits shear/deg_diff from reconstruct-meso data
   - Creates dual configs (reconstruct-meso + rep-year)

2. fill-heights:
   - Executes fill-heights from configuration file
   - Applies interpolation/extrapolation to data
   - Saves filled columns to output

Workflow:
========

    Step 1: Run reconstruct-meso processing
    ┌─────────────────────────────────────┐
    │  cleanmast process reconstruct-meso │
    └─────────────────────────────────────┘
            │
            ▼
    Step 2: (Optional) Run representative-year
    ┌─────────────────────────────────────┐
    │  cleanmast process representative-year │
    └─────────────────────────────────────┘
            │
            ▼
    Step 3: Generate fill-heights configs
    ┌─────────────────────────────────────────────────┐
    │  cleanmast recommend fill-heights -h 120,140,160 │
    └─────────────────────────────────────────────────┘
            │
            ▼
    Step 4: Execute fill-heights
    ┌─────────────────────────────────────────────────┐
    │  cleanmast fill-heights fill-heights-reconstruct-meso.toml │
    └─────────────────────────────────────────────────┘
            │
            ▼
    Step 5: (Optional) Execute for representative-year
    ┌─────────────────────────────────────────────────┐
    │  cleanmast fill-heights fill-heights-representative-year.toml │
    └─────────────────────────────────────────────────┘

Output Files:
=============

-reconstruct-meso- fill-heights.toml:
    Configuration for filling reconstruct-meso output

- fill-heights-representative-year.toml:
    Configuration for filling representative-year output (if available)

- filled-heights/{mast}.parquet:
    Output data with filled columns

- filled-heights/{mast}.sensors.yaml:
    Updated sensor metadata

Note: This module re-exports validation functions for backward compatibility.
The actual command implementations are in the commands module.
"""

import click

from .commands.recommend import recommend_fill_heights
from .commands.execute import fill_heights

# Re-export validation functions for backward compatibility
from .recommend.validation import (
    _build_sensor_column_map,
    _validate_references,
    _validate_single_reference,
)

__all__ = [
    "recommend_fill_heights",
    "fill_heights",
    "_build_sensor_column_map",
    "_validate_references",
    "_validate_single_reference",
]
