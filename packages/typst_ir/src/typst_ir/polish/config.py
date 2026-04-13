"""TOML configuration parser for the docx-polish IR system.

Provides Pydantic models and a ``load_config`` entry point for reading polish
configuration from TOML files.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError


class StyleConfig(BaseModel):
    """Style configuration for a single document style."""

    model_config = ConfigDict(extra="forbid")

    font_name: str | None = None
    font_name_chinese: str | None = None
    font_name_latin: str | None = None
    font_size: float | None = None
    font_style: str | None = None
    font_color: str | None = None
    line_spacing_before: float | None = None
    line_spacing_after: float | None = None
    line_spacing: float | None = None


class RenumberConfig(BaseModel):
    """Renumbering options for headings, figures, and tables."""

    model_config = ConfigDict(extra="forbid")

    headings: bool = True
    figures: bool = True
    tables: bool = True


class PolishConfig(BaseModel):
    """Top-level polish configuration."""

    model_config = ConfigDict(extra="forbid")

    styles: dict[str, StyleConfig]
    renumber: RenumberConfig


def load_config(path: Path) -> PolishConfig:
    """Load and validate a TOML polish configuration file.

    Args:
        path: Path to the TOML configuration file.

    Returns:
        A validated ``PolishConfig`` instance.

    Raises:
        ValueError: If the file does not exist, contains unknown keys, or fails
            Pydantic validation.
    """
    if not path.exists():
        raise ValueError(f"Configuration file not found: {path}")

    with path.open("rb") as f:
        raw = tomllib.load(f)

    try:
        return PolishConfig.model_validate(raw)
    except ValidationError as exc:
        errors = exc.errors()
        messages = []
        for err in errors[:5]:
            loc = ".".join(str(part) for part in err["loc"])
            msg = err["msg"]
            messages.append(f"  - {loc}: {msg}")
        detail = "\n".join(messages)
        raise ValueError(
            f"Invalid configuration in '{path}':\n{detail}"
        ) from exc
