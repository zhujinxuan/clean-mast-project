"""Tree builder for converting flat subsection list to hierarchical tree.

Ported from assessment's domain/value_objects/tree_builder.py.
# LOGIC-PRESERVATION: algorithm and behavior intentionally mirror the
assessment implementation; only the SectionNode container is made frozen
and children are stored as a tuple instead of a mutable list.
"""

from __future__ import annotations

from cleanmast.subdomains.configuration.model.report_config import FlatSubsectionConfig
from cleanmast.subdomains.reporting.model.section_node import SectionNode, parse_index


def sort_subsections(
    subsections: list[FlatSubsectionConfig],
) -> list[FlatSubsectionConfig]:
    """Sort subsections by their hierarchical index numerically.

    Uses numeric segment comparison so "2.4.10" comes after "2.4.2",
    not before it as would happen with lexical string sorting.

    Args:
        subsections: List of FlatSubsectionConfig to sort.

    Returns:
        New list sorted by parsed index in ascending order.
    """
    return sorted(subsections, key=lambda s: parse_index(s.index))


def _collect_all_indices(actual: dict[str, FlatSubsectionConfig]) -> set[str]:
    """Collect all indices including parent prefixes for intermediate nodes."""
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
    """Create SectionNode instances for every index (actual or placeholder)."""
    nodes: dict[str, SectionNode] = {}
    for idx in sorted(all_indices, key=lambda x: parse_index(x)):
        if idx in actual:
            sub = actual[idx]
            nodes[idx] = SectionNode(
                index=sub.index,
                type=sub.type,
                title=sub.title,
                datasets=tuple(sub.datasets),
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
    """Link child nodes to their parents and return sorted root nodes."""
    children_by_parent: dict[str, list[SectionNode]] = {}
    roots: list[SectionNode] = []

    for idx, node in nodes.items():
        parts = idx.split(".")
        if len(parts) == 1:
            roots.append(node)
        else:
            parent_idx = ".".join(parts[:-1])
            if parent_idx in nodes:
                children_by_parent.setdefault(parent_idx, []).append(node)
            else:
                roots.append(node)

    def _rebuild(node: SectionNode) -> SectionNode:
        kids = children_by_parent.get(node.index, [])
        if not kids:
            return node
        sorted_kids = sorted(kids, key=lambda n: parse_index(n.index))
        return SectionNode(
            index=node.index,
            type=node.type,
            title=node.title,
            datasets=node.datasets,
            is_placeholder=node.is_placeholder,
            children=tuple(_rebuild(k) for k in sorted_kids),
        )

    roots = [_rebuild(r) for r in roots]
    roots.sort(key=lambda n: parse_index(n.index))
    return roots


def _fill_placeholder_siblings(siblings: list[SectionNode]) -> list[SectionNode]:
    """Fill gaps in sibling sequences with placeholder nodes.

    Recursively processes children of each sibling. Because SectionNode is
    frozen, this returns new nodes rather than mutating in place.
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
            node = positions[i]
        else:
            node = SectionNode(
                index=f"{parent_prefix}{i}",
                type="timeseries",
                title="Placeholder",
                datasets=None,
                is_placeholder=True,
            )

        if node.children:
            node = SectionNode(
                index=node.index,
                type=node.type,
                title=node.title,
                datasets=node.datasets,
                is_placeholder=node.is_placeholder,
                children=tuple(_fill_placeholder_siblings(list(node.children))),
            )
        filled.append(node)

    return filled


def build_section_tree(
    subsections: list[FlatSubsectionConfig],
) -> list[SectionNode]:
    """Convert a flat list of subsections into a hierarchical tree.

    Groups subsections by parent prefix and auto-creates placeholder parents
    for missing intermediate nodes.

    Args:
        subsections: Flat list of subsection configurations.

    Returns:
        Sorted list of root SectionNode instances.
    """
    if not subsections:
        return []

    sorted_subs = sort_subsections(subsections)
    actual: dict[str, FlatSubsectionConfig] = {s.index: s for s in sorted_subs}

    all_indices = _collect_all_indices(actual)
    nodes = _create_nodes(all_indices, actual)
    roots = _link_children(nodes)
    roots = _fill_placeholder_siblings(roots)

    return roots

