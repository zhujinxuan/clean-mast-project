"""config_io — the single entry point for all TOML I/O in cleanmast.

``load_config(T, path)`` parses a TOML file into a Pydantic model.
``save_config(model, path)`` writes a Pydantic model to a TOML file.
These two functions are the ONLY callers of ``tomli`` and ``tomli_w`` in the
entire package — enforced by the ``tomli-configuration-gateway-only``
import-linter contract in ``.importlinter``.

ProjectConfig delegates to them; execute commands use them directly.
"""

from pathlib import Path
from typing import TypeVar

import tomli
import tomli_w
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def load_config(config_type: type[T], config_path: str | Path) -> T:
    """Parse a TOML config from the exact path, validated against config_type."""
    config_path = Path(config_path)
    with open(config_path, "rb") as f:
        data = tomli.load(f)
    return config_type(**data)


def save_config(model: BaseModel, config_path: str | Path) -> None:
    """Write a Pydantic model to a TOML file.

    ``None``-valued fields are omitted (TOML has no null); JSON mode
    normalizes enums, datetimes, and paths into TOML-serializable values.
    """
    config_path = Path(config_path)
    data = model.model_dump(mode="json", exclude_none=True)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)
