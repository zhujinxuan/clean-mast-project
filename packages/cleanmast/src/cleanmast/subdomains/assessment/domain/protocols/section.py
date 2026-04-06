"""Report protocols.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-002-context-maps
Compliance: Subdomain layout ✓ | Protocol Definition ✓
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from cleanmast.subdomains.assessment.domain.types import TypstChild
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@runtime_checkable
class Section(Protocol):
    """Protocol for report sections with customizable rendering.

    Any class implementing title, level, atoms, and render()
    can be used as a section in ReportBuilder. This allows for
    different rendering strategies (Jinja2 templates, hardcoded layouts,
    dynamic generation, etc.) while maintaining a common interface.

    Example:
        >>> section: Section = TemplatedSection("Analysis", 1, template, atoms)
        >>> isinstance(section, Section)
        True
        >>> markup = section.render(Path("images"))

    Attributes:
        title: Section title displayed in document
        level: Heading level (1=section, 2=subsection)
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
    def level(self) -> int:
        """Heading level (1=section, 2=subsection).

        Returns:
            Integer level for Typst heading (1 -> ==, 2 -> ===)
        """
        ...

    @property
    def atoms(self) -> AtomCollection:
        """Collection of atoms in this section.

        Returns:
            AtomCollection containing all report atoms for this section
        """
        ...

    def render(self, images_dir: Path) -> str:
        """Render section to Typst markup.

        Each implementation defines its own rendering strategy.
        Can use Jinja2 templates, hardcoded Python logic, or
        other approaches.

        Args:
            images_dir: Directory where atom images are stored

        Returns:
            Typst markup string for the section

        Example:
            >>> section = WindRoseSection("风向分析", 1, atoms)
            >>> markup = section.render(Path("images"))
            >>> print(markup[:50])
            == 风向分析

            ...
        """
        ...

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section to IR nodes.

        Returns a list of TypstChild nodes representing this section's content.
        Default implementation returns empty list for backward compatibility.

        Args:
            images_dir: Directory for generated images

        Returns:
            List of IR nodes (headings, figures, tables, paragraphs)
        """
        return []
