"""Shared subsection rendering utility.

Port of assessment's render_subsection_content, adapted for reporting types.
Takes a sequence of ReportAtom and groups by type internally (no AtomCollection
dependency). Renders content in three-phase order: summaries → tables → figures.
"""

from pathlib import Path
from typing import Sequence

from typst_ir import TypstParagraph
from typst_ir.nodes import TypstBodyBlock

from cleanmast.subdomains.reporting.compute.merge import merge_paragraphs
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom


def render_subsection_content(
    atoms: Sequence[ReportAtom],
    atom_configs: list[tuple[type[ReportAtom], bool]],
    images_dir: Path,
) -> list[TypstBodyBlock]:
    """Render subsection body content with global three-phase ordering.

    Phase 1: Collect and merge summary paragraphs for each atom type where
    has_summary is True.
    Phase 2: Collect all tables for each atom type.
    Phase 3: Collect all figures for each atom type.

    Empty content is skipped entirely.

    Args:
        atoms: Sequence of ReportAtom instances to render.
        atom_configs: List of (atom_type, has_summary) tuples defining
            the atom types to render and whether to include summaries.
        images_dir: Directory for image output.

    Returns:
        List of TypstBodyBlock nodes in three-phase order.
    """
    # Group atoms by type for efficient lookup
    atoms_by_type: dict[type[ReportAtom], list[ReportAtom]] = {}
    for atom in atoms:
        atom_type = type(atom)
        atoms_by_type.setdefault(atom_type, []).append(atom)

    result: list[TypstBodyBlock] = []
    texts: list[TypstParagraph] = []
    tables: list[TypstBodyBlock] = []
    figures: list[TypstBodyBlock] = []

    for atom_type, has_summary in atom_configs:
        typed_atoms = atoms_by_type.get(atom_type, [])
        if not typed_atoms:
            continue

        if has_summary:
            summaries: list[TypstParagraph] = []
            for atom in typed_atoms:
                rendered = atom.renderSummary()
                if rendered:
                    summaries.extend(rendered)
            if summaries:
                merged = merge_paragraphs(summaries)
                if merged.text:
                    texts.append(merged)

        for atom in typed_atoms:
            table = atom.renderTable()
            if table is not None:
                tables.append(table)

        for atom in typed_atoms:
            figure = atom.renderImageTypst(images_dir)
            if figure is not None:
                figures.append(figure)

    result.extend(texts)
    result.extend(tables)
    result.extend(figures)
    return result
