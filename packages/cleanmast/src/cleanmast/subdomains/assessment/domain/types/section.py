from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typst_ir.nodes import TypstBodyBlock, TypstHeading


class Section(BaseModel):
    """Document-AST section mirroring typst_ir.TypstSection for cleanmast report building."""

    heading: TypstHeading
    body: list[TypstBodyBlock]
    subsections: list["Section"]

    model_config = ConfigDict(frozen=True)
