"""Report protocols.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-002-context-maps
Compliance: Subdomain layout ✓ | Protocol Definition ✓
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from cleanmast.subdomains.assessment.shared.ir_types import TypstSection
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@runtime_checkable
class Section(Protocol):
    """Protocol for report sections with IR-based rendering.

    Any class implementing title, atoms, and render_ir()
    can be used as a section in ReportBuilder. This allows for
    different rendering strategies while maintaining a common interface.

    Example:
        >>> section: Section = WindRoseSection("风向分析", atoms)
        >>> isinstance(section, Section)
        True
        >>> section_node = section.render_ir(Path("images"))

    Attributes:
        title: Section title displayed in document
        atoms: Collection of report atoms in this section
    """

    @property
    def title(self) -> str:
        """Section title for document heading.

        Returns:
            String title displayed as section header
        """
        ...

    @property
    def atoms(self) -> AtomCollection:
        """Collection of atoms in this section.

        Returns:
            AtomCollection containing all report atoms for this section
        """
        ...

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Returns a TypstSection representing this section's content.

        Args:
            images_dir: Directory for generated images

        Returns:
            TypstSection with heading, body, and subsections
        """
        ...
