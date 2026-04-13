"""Polish IR submodule for docx style and numbering operations.

Provides frozen Pydantic models for representing polish instructions
that can be serialized to JSON and applied to DOCX documents.
"""

from typst_ir.polish.types import (
    PolishIR,
    RenumberOp,
    StyleOp,
)

__all__ = [
    "PolishIR",
    "RenumberOp",
    "StyleOp",
]
