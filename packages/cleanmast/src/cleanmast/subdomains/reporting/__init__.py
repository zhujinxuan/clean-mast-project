"""Reporting subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Subdomain layout ✓ | Reporting Domain ✓
"""

from cleanmast.subdomains.reporting.entities import ReportAtom
from cleanmast.subdomains.reporting.services import (
    ReportBuilder,
    TypstRenderer,
    compile_typst_to_pdf,
    compile_typst_to_docx,
)
from cleanmast.subdomains.reporting.protocols import Section
from cleanmast.subdomains.reporting.value_objects.collections import AtomCollection

__all__ = [
    # Entities
    "ReportAtom",
    # Services
    "ReportBuilder",
    "TypstRenderer",
    "compile_typst_to_pdf",
    "compile_typst_to_docx",
    # Protocols
    "Section",
    # Value Objects
    "AtomCollection",
]
