"""Mapping package for IR to source document location tracking.

Provides types and utilities for mapping between Typst IR nodes and their
original source locations in input documents (e.g., DOCX paragraphs).
"""

from __future__ import annotations

from typst_ir.mapping.builder import MappingBuilder
from typst_ir.mapping.cli import main
from typst_ir.mapping.detection import DetectionResult
from typst_ir.mapping.injector import extract_paragraphs, inject_ids
from typst_ir.mapping.matcher import DocxMatcher
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import (
    ConfidenceLevel,
    DetectionMethod,
    DocxTypstMapping,
    MappingEntry,
    NodeID,
)

__all__ = [
    # Types
    "NodeID",
    "NodeRegistry",
    "MappingEntry",
    "DocxTypstMapping",
    "DetectionMethod",
    "ConfidenceLevel",
    "DetectionResult",
    "DocxMatcher",
    # Builder and orchestration
    "MappingBuilder",
    # ID injection utilities
    "inject_ids",
    "extract_paragraphs",
    # CLI entry point
    "main",
]
