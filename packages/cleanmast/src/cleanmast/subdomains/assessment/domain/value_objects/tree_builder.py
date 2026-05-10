"""Tree builder for converting flat subsection list to hierarchical tree.

ADR-GUARDRAILS: ddd-vo-001-value-objects, types-001-strict-type-safety
Compliance: Value Object ✓ | Strict types ✓
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cleanmast.subdomains.assessment.domain.value_objects.flat_subsection_config import (
    FlatSubsectionConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.index_utils import (
    parse_index,
    sort_subsections,
)


@dataclass
class SectionNode:
    """Node in a hierarchical section tree.

    Internal tree structure (not config) — uses dataclass, not Pydantic.
    """

    index: str
    type: str
    title: str | None = None
    datasets: list[str] | None = None
    is_placeholder: bool = False
    children: list[SectionNode] = field(default_factory=list)


def _collect_all_indices(actual: dict[str, FlatSubsectionConfig]) -> set[str]:
    """Collect all indices including parent prefixes for intermediate nodes.

    Args:
        actual: Mapping of subsection index to its config.

    Returns:
        Set of all indices (actual + derived parent prefixes).
    """
    all_indices: set[str] = set(actual.keys())
    for idx in list(actual.keys()):
        parts = idx.split(".")
        for i in range(1, len(parts)):
            parent_idx = ".".join(parts[:i])
            all_indices.add(parent_idx)
    return all_indices


def _create_nodes(
    all_indices: set[str], actual: dict[str, FlatSubsectionConfig]
) -> dict[str, SectionNode]:
    """Create SectionNode instances for every index (actual or placeholder).

    Args:
        all_indices: All indices including derived parent prefixes.
        actual: Mapping of subsection index to its config.

    Returns:
        Mapping of index to created SectionNode.
    """
    nodes: dict[str, SectionNode] = {}
    for idx in sorted(all_indices, key=lambda x: parse_index(x)):
        if idx in actual:
            sub = actual[idx]
            nodes[idx] = SectionNode(
                index=sub.index,
                type=sub.type,
                title=sub.title,
                datasets=sub.datasets,
            )
        else:
            nodes[idx] = SectionNode(
                index=idx,
                type="timeseries",
                title="Placeholder",
                datasets=None,
                is_placeholder=True,
            )
    return nodes


def _link_children(nodes: dict[str, SectionNode]) -> list[SectionNode]:
    """Link child nodes to their parents and return sorted root nodes.

    Args:
        nodes: Mapping of index to SectionNode.

    Returns:
        Sorted list of root SectionNode instances.
    """
    roots: list[SectionNode] = []
    for idx, node in nodes.items():
        parts = idx.split(".")
        if len(parts) == 1:
            roots.append(node)
        else:
            parent_idx = ".".join(parts[:-1])
            if parent_idx in nodes:
                parent = nodes[parent_idx]
                parent.children.append(node)
            else:
                roots.append(node)

    roots.sort(key=lambda n: parse_index(n.index))
    return roots


def _propagate_datasets(roots: list[SectionNode]) -> None:
    """Propagate parent datasets down to children with None datasets.

    Mutates nodes in-place.

    Args:
        roots: Root nodes to start propagation from.
    """
    def _propagate(node: SectionNode, parent_datasets: list[str] | None) -> None:
        if node.datasets is None:
            node.datasets = parent_datasets
        for child in node.children:
            _propagate(child, node.datasets)

    for root in roots:
        _propagate(root, None)


def _fill_placeholder_siblings(siblings: list[SectionNode]) -> list[SectionNode]:
    """Fill gaps in sibling sequences with placeholder nodes.

    Recursively processes children of each sibling.

    Args:
        siblings: List of sibling SectionNode instances at the same level.

    Returns:
        List of siblings with gaps filled by placeholder nodes.
    """
    if not siblings:
        return siblings

    positions: dict[int, SectionNode] = {}
    for node in siblings:
        parts = node.index.split(".")
        pos = int(parts[-1])
        positions[pos] = node

    max_pos = max(positions.keys())
    parent_prefix = ""
    first_idx = siblings[0].index
    if "." in first_idx:
        parent_prefix = first_idx.rsplit(".", 1)[0] + "."

    filled: list[SectionNode] = []
    for i in range(1, max_pos + 1):
        if i in positions:
            filled.append(positions[i])
        else:
            placeholder = SectionNode(
                index=f"{parent_prefix}{i}",
                type="timeseries",
                title="Placeholder",
                datasets=None,
                is_placeholder=True,
            )
            filled.append(placeholder)

    for node in filled:
        if node.children:
            node.children = _fill_placeholder_siblings(node.children)

    return filled


def build_section_tree(
    subsections: list[FlatSubsectionConfig],
) -> list[SectionNode]:
    """Convert a flat list of subsections into a hierarchical tree.

    Groups subsections by parent prefix, auto-creates placeholder parents
    for missing intermediate nodes, and propagates datasets downward.

    Args:
        subsections: Flat list of subsection configurations

    Returns:
        Sorted list of root SectionNode instances
    """
    if not subsections:
        return []

    sorted_subs = sort_subsections(subsections)
    actual: dict[str, FlatSubsectionConfig] = {s.index: s for s in sorted_subs}

    all_indices = _collect_all_indices(actual)
    nodes = _create_nodes(all_indices, actual)
    roots = _link_children(nodes)
    _propagate_datasets(roots)
    roots = _fill_placeholder_siblings(roots)

    return roots


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
                    type=node.type,
                    title=node.title,
                    datasets=node.datasets,
                )
            )
        for child in node.children:
            _walk(child)

    for root in roots:
        _walk(root)

    result.sort(key=lambda s: parse_index(s.index))
    return result
