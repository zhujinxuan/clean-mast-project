"""Index parsing and sorting utilities for flat subsection configurations."""

from __future__ import annotations

from cleanmast.subdomains.assessment.domain.value_objects.flat_subsection_config import (
    FlatSubsectionConfig,
)


def parse_index(index: str) -> tuple[int, ...]:
    """Parse a hierarchical index string into a tuple of integers.

    Splits the index on '.' and converts each segment to an integer.
    Used as a sort key for numeric segment sorting.

    Args:
        index: A dot-separated index string like "2.4.1" or "10"

    Returns:
        Tuple of integer segments

    Raises:
        ValueError: If index is empty or contains empty segments
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


def sort_subsections(
    subsections: list[FlatSubsectionConfig],
) -> list[FlatSubsectionConfig]:
    """Sort subsections by their hierarchical index numerically.

    Uses numeric segment comparison so "2.4.10" comes after "2.4.2",
    not before it as would happen with lexical string sorting.

    Args:
        subsections: List of FlatSubsectionConfig to sort

    Returns:
        New list sorted by parsed index in ascending order
    """
    return sorted(subsections, key=lambda s: parse_index(s.index))
