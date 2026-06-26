"""Section protocol for reporting capabilities.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-002-context-maps
Compliance: Subdomain layout ✓ | Protocol Definition ✓
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from typst_ir import TypstSection


@runtime_checkable
class Section(Protocol):
    """Protocol for report sections with IR-based rendering.

    Any class implementing render_ir() can be used as a section
    in ReportBuilder. This allows for different rendering strategies
    while maintaining a common interface.

    Example:
        >>> section: Section = WindRoseSection("Wind Rose", atoms)
        >>> isinstance(section, Section)
        True
        >>> section_node = section.render_ir(Path("images"))
    """

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Returns a TypstSection representing this section's content.

        Args:
            images_dir: Directory for generated images

        Returns:
            TypstSection with heading, body, and subsections
        """
        ...
