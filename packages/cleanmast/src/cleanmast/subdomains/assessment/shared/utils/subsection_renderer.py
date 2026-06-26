"""Shared subsection rendering utility.
 
ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""
 
from pathlib import Path
 
from typst_ir.nodes import TypstBodyBlock
 
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.shared.utils.merge import merge_paragraphs
from cleanmast.subdomains.assessment.shared.ir_types import TypstParagraph
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
 
 
def render_subsection_content(
    collection: AtomCollection,
    atom_configs: list[tuple[type[ReportAtom], bool]],
    images_dir: Path,
) -> list[TypstBodyBlock]:
    """Render subsection body content with global three-phase ordering.
 
    Phase 1: Collect and merge summary paragraphs across all masts for each
    atom type where has_summary is True.
    Phase 2: Collect all tables across masts for each atom type.
    Phase 3: Collect all figures across masts for each atom type.
 
    Empty content is skipped entirely.
 
    Args:
        collection: AtomCollection containing atoms across masts.
        atom_configs: List of (atom_type, has_summary) tuples defining
            the atom types to render and whether to include summaries.
        images_dir: Directory for image output.
 
    Returns:
        List of TypstBodyBlock nodes in three-phase order.
    """
    result: list[TypstBodyBlock] = []
 
    texts: list[TypstParagraph] = []
    tables: list[TypstBodyBlock] = []
    figures: list[TypstBodyBlock] = []
 
    for atom_type, has_summary in atom_configs:
        atoms = collection.get_all_by_type(atom_type)
        if not atoms:
            continue
 
        if has_summary:
            summaries = []
            for atom in atoms:
                rendered = atom.renderSummary()
                if rendered:
                    summaries.extend(rendered)
            if summaries:
                merged = merge_paragraphs(summaries)
                if merged.text:
                    texts.append(merged)
 
        for atom in atoms:
            table = atom.renderTable()
            if table is None:
                continue
            tables.append(table)
 
        for atom in atoms:
            figure = atom.renderImageTypst(images_dir)
            if figure is not None:
                figures.append(figure)
 
    result.extend(texts)
    result.extend(tables)
    result.extend(figures)
    return result
