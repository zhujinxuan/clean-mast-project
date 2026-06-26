"""Paragraph merge utilities for reporting capabilities.

# LOGIC-PRESERVATION: Ported from assessment/shared/utils/merge.py.
Behaviour preserved exactly.
Pure functions only — no IO, no side effects.
"""

from typst_ir import TypstParagraph


def merge_paragraphs(paragraphs: list[TypstParagraph], sep: str = " ") -> TypstParagraph:
    """Merge multiple TypstParagraph instances into one.

    Joins the `.text` fields of the given paragraphs with `sep`.
    Paragraphs whose text is empty or contains only whitespace are skipped.

    Args:
        paragraphs: List of TypstParagraph instances to merge.
        sep: Separator string used between paragraph texts.

    Returns:
        A new TypstParagraph containing the joined text.
    """
    texts = [p.text for p in paragraphs if p.text.strip()]
    return TypstParagraph(text=sep.join(texts))
