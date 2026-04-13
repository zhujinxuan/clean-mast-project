"""NodeRegistry for caching NodeIDs and building path index.

Provides efficient lookup of NodeIDs for IR nodes with path-based indexing
and document-wide hash computation for unique identification.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypeAlias, cast

from typst_ir.mapping.types import NodeID
from typst_ir.nodes import (
    TypstBlock,
    TypstDocument,
    TypstHeading,
    TypstSection,
)

# Type alias for any node that can be indexed (document or block)
TypstNode: TypeAlias = TypstDocument | TypstBlock


class NodeRegistry:
    """Registry for caching NodeIDs and building path index.

    Maintains a cache mapping node object IDs to NodeID instances, a path
    index for fast lookup by path, and computes document-wide hash once
    for efficient node identification.

    Attributes:
        _cache: Maps `id(node)` to cached NodeID instance
        _path_index: Maps path string to node instance
        _full_hash: Document-wide hash computed once during initialization
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._cache: dict[int, NodeID] = {}
        self._path_index: dict[str, TypstNode] = {}
        self._full_hash: str = ""

    def initialize(self, document: TypstDocument) -> None:
        """Initialize registry with document.

        Builds path index for all nodes and computes document-wide hash.
        Must be called before using get_id().

        Args:
            document: Root document to index

        Raises:
            TypeError: If document doesn't have required attributes
        """
        # Use duck typing to support documents from different import paths
        if not hasattr(document, "children"):
            raise TypeError(
                f"Expected TypstDocument root, got {type(document).__name__}"
            )

        # Reset state
        self._cache = {}
        self._path_index = {}

        # Compute full document hash once
        self._full_hash = self._compute_full_hash(document)

        # Build path index for all nodes
        self._build_path_index(document, "doc")

    def get_id(self, node: TypstNode) -> NodeID:
        """Get NodeID for a node, using cache if available.

        Args:
            node: IR node to get ID for

        Returns:
            NodeID with path, full_hash, and node_hash

        Raises:
            KeyError: If node not found in path index (initialize not called)
        """
        node_id = id(node)

        # Return cached NodeID if available
        if node_id in self._cache:
            return self._cache[node_id]

        # Find path for this node
        path = self._find_path(node)
        if path is None:
            raise KeyError(
                f"Node {type(node).__name__} not found in path index. "
                "Did you call initialize()?"
            )

        # Compute node-specific hash
        node_hash = self._compute_node_hash(node)

        # Create and cache NodeID
        node_id_obj = NodeID(
            path=path,
            full_hash=self._full_hash,
            node_hash=node_hash,
        )
        self._cache[node_id] = node_id_obj

        return node_id_obj

    def _find_path(self, node: TypstNode) -> str | None:
        """Find path for a node by searching path_index.

        Args:
            node: Node to find path for

        Returns:
            Path string or None if not found
        """
        for path, indexed_node in self._path_index.items():
            if indexed_node is node:
                return path
        return None

    def _build_path_index(self, node: TypstNode, path: str) -> None:
        """Recursively build path index for all nodes.

        Uses duck typing to handle all 11 node types without explicit
        isinstance checks. Paths include type names for identification.

        Args:
            node: Current node to index
            path: Path string for this node (e.g., "doc.children[0:TypstParagraph]")
        """
        # Add this node to index
        self._path_index[path] = node

        # Recurse into children based on node type (duck typing)
        # 1. TypstDocument - has children
        if hasattr(node, "children") and not hasattr(node, "heading"):
            # Document children (sections-only)
            children = cast(list[TypstSection], node.children)
            for idx, child in enumerate(children):
                child_type = type(child).__name__
                self._build_path_index(child, f"{path}.children.{idx}[{child_type}]")

        # 2. TypstSection - has heading, body, and subsections
        elif hasattr(node, "heading") and hasattr(node, "body") and hasattr(node, "subsections"):
            section_heading = cast(TypstHeading, node.heading)
            self._build_path_index(section_heading, f"{path}.heading[TypstHeading]")
            body_items = cast(list[TypstNode], node.body)
            for idx, item in enumerate(body_items):
                item_type = type(item).__name__
                self._build_path_index(item, f"{path}.body.{idx}[{item_type}]")
            subsections = cast(list[TypstNode], node.subsections)
            for idx, sub in enumerate(subsections):
                self._build_path_index(sub, f"{path}.subsections.{idx}[TypstSection]")

        # 3. TypstBulletList - has items (list of lists)
        elif hasattr(node, "items") and not hasattr(node, "start"):
            items = cast(list[list[TypstNode]], node.items)
            for item_idx, item in enumerate(items):
                for block_idx, block in enumerate(item):
                    block_type = type(block).__name__
                    self._build_path_index(
                        block, f"{path}.items.{item_idx}.{block_idx}[{block_type}]"
                    )

        # 4. TypstOrderedList - has items and start
        elif hasattr(node, "items") and hasattr(node, "start"):
            items = cast(list[list[TypstNode]], node.items)
            for item_idx, item in enumerate(items):
                for block_idx, block in enumerate(item):
                    block_type = type(block).__name__
                    self._build_path_index(
                        block, f"{path}.items.{item_idx}.{block_idx}[{block_type}]"
                    )

        # Leaf nodes (no children to recurse):
        # - TypstHeading (text, level)
        # - TypstParagraph (text)
        # - TypstTable (data, headers, caption)
        # - TypstFigure (content, caption, kind)
        # - TypstEquation (latex, display)
        # - TypstCodeBlock (text, language)
        # - TypstRawBlock (format, text)
        # These are handled by the base case (adding to index)

    def _compute_full_hash(self, document: TypstDocument) -> str:
        """Compute document-wide hash.

        Creates a deterministic hash of the entire document structure
        by serializing to JSON and hashing.

        Args:
            document: Root document to hash

        Returns:
            Hex digest of document hash
        """
        # Serialize document to JSON for hashing
        json_str = document.model_dump_json()

        # Compute SHA-256 hash
        hasher = hashlib.sha256()
        hasher.update(json_str.encode("utf-8"))
        return hasher.hexdigest()

    def _compute_node_hash(self, node: TypstNode) -> str:
        """Compute node-specific hash.

        Creates a deterministic hash of a node's content by serializing
        to JSON and hashing.

        Args:
            node: Node to hash

        Returns:
            Hex digest of node hash
        """
        # Get node data as dict for hashing
        if hasattr(node, "model_dump"):
            # Pydantic model
            data = node.model_dump()
        else:
            # Fallback: convert to dict manually
            data = self._node_to_dict(node)

        # Serialize to canonical JSON
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=True)

        # Compute SHA-256 hash
        hasher = hashlib.sha256()
        hasher.update(json_str.encode("utf-8"))
        return hasher.hexdigest()

    def _node_to_dict(self, node: Any) -> dict[str, Any]:
        """Convert a node to dictionary representation.

        Uses duck typing to extract attributes from any node type.

        Args:
            node: Node to convert

        Returns:
            Dictionary with node data
        """
        result: dict[str, Any] = {}

        # Document has children; Section has body + subsections
        if hasattr(node, "children") and not hasattr(node, "heading"):
            # TypstDocument
            result["children"] = [
                self._node_to_dict(child) for child in node.children
            ]

        if hasattr(node, "heading"):
            # Section heading
            result["heading"] = self._node_to_dict(node.heading)
            # Section body and subsections
            if hasattr(node, "body"):
                result["body"] = [
                    self._node_to_dict(item) for item in node.body
                ]
            if hasattr(node, "subsections"):
                result["subsections"] = [
                    self._node_to_dict(sub) for sub in node.subsections
                ]

        if hasattr(node, "text"):
            result["text"] = node.text

        if hasattr(node, "data"):
            result["data"] = node.data

        if hasattr(node, "headers"):
            result["headers"] = node.headers

        if hasattr(node, "caption"):
            result["caption"] = node.caption

        if hasattr(node, "content"):
            result["content"] = node.content

        if hasattr(node, "kind"):
            result["kind"] = node.kind

        if hasattr(node, "latex"):
            result["latex"] = node.latex

        if hasattr(node, "display"):
            result["display"] = node.display

        if hasattr(node, "language"):
            result["language"] = node.language

        if hasattr(node, "format"):
            result["format"] = node.format

        if hasattr(node, "items"):
            # List items (list of lists of blocks)
            result["items"] = [
                [self._node_to_dict(block) for block in item]
                for item in node.items
            ]

        if hasattr(node, "start"):
            result["start"] = node.start

        return result

    @property
    def full_hash(self) -> str:
        """Get the document-wide hash.

        Returns:
            Document hash computed during initialization
        """
        return self._full_hash

    @property
    def path_index(self) -> dict[str, TypstNode]:
        """Get the path index mapping.

        Returns:
            Dictionary mapping paths to nodes
        """
        return self._path_index.copy()
