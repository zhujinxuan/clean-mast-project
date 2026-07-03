"""Section node data type and flatten_tree utility for the reporting pipeline.

SectionNode is the data structure for hierarchical section trees.
flatten_tree provides round-trip conversion back to flat config form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cleanmast.subdomains.configuration.model.report_config import SubsectionType

from cleanmast.subdomains.configuration.model.report_config import FlatSubsectionConfig


def parse_index(index: str) -> tuple[int, ...]:
    """Parse a hierarchical index string into a tuple of integers.

    Args:
        index: A dot-separated index string like "2.4.1" or "10".

    Returns:
        Tuple of integer segments.

    Raises:
        ValueError: If index is empty or contains empty segments.
    """
    if not index:
        raise ValueError("Index cannot be empty")

    segments = index.split(".")
    result: list[int] = []
    for seg in segments:
        if not seg:
            raise ValueError(f"Empty segment in index: {index}")
        result.append(int(seg))

    return tuple(result)


@dataclass(frozen=True)
class SectionNode:
    """Node in a hierarchical section tree.

    Internal tree structure (not config) — frozen dataclass with immutable
    tuple children, unlike the mutable assessment version.
    """

    index: str
    type: str
    title: str | None = None
    datasets: tuple[str, ...] | None = None
    is_placeholder: bool = False
    children: tuple["SectionNode", ...] = ()


def flatten_tree(roots: list[SectionNode]) -> list[FlatSubsectionConfig]:
    """Flatten a hierarchical section tree back to sorted flat list.

    Only non-placeholder nodes (is_placeholder=False) are included.
    Output is sorted by parsed index.
    """
    result: list[FlatSubsectionConfig] = []

    def _walk(node: SectionNode) -> None:
        if not node.is_placeholder:
            result.append(
                FlatSubsectionConfig(
                    index=node.index,
                    type=cast("SubsectionType", node.type),
                    title=node.title,
                    datasets=list(node.datasets) if node.datasets is not None else [],
                )
            )
        for child in node.children:
            _walk(child)

    for root in roots:
        _walk(root)

    result.sort(key=lambda s: parse_index(s.index))
    return result
