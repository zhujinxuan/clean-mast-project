"""Tests for NodeRegistry class.

Tests caching behavior, path index building, and hash computation
for all 11 node types.
"""

from __future__ import annotations

import pytest
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import NodeID
from typst_ir.nodes import (
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstSection,
    TypstTable,
)


class TestNodeRegistryInitialization:
    """Test registry initialization and basic functionality."""

    def test_initialize_computes_full_hash(self) -> None:
        """initialize() should compute full_hash once for document."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Hello")],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()

        assert registry.full_hash == ""
        registry.initialize(doc)
        assert registry.full_hash != ""
        assert len(registry.full_hash) == 64  # SHA-256 hex digest length

    def test_initialize_builds_path_index(self) -> None:
        """initialize() should build path index for all nodes."""
        heading = TypstHeading(text="Title")
        para = TypstParagraph(text="Content")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Title"),
                body=[heading, para],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()

        registry.initialize(doc)

        assert "doc" in registry.path_index
        assert "doc.children.0[TypstSection]" in registry.path_index
        assert "doc.children.0[TypstSection].body.0[TypstHeading]" in registry.path_index
        assert "doc.children.0[TypstSection].body.1[TypstParagraph]" in registry.path_index
        assert registry.path_index["doc"] is doc
        assert registry.path_index["doc.children.0[TypstSection].body.0[TypstHeading]"] is heading
        assert registry.path_index["doc.children.0[TypstSection].body.1[TypstParagraph]"] is para

    def test_initialize_resets_previous_state(self) -> None:
        """initialize() should reset cache and index from previous document."""
        doc1 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Doc 1")],
                subsections=[],
            ),
        ])
        doc2 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Doc 2")],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()

        registry.initialize(doc1)
        hash1 = registry.full_hash
        id1 = registry.get_id(doc1)

        registry.initialize(doc2)
        hash2 = registry.full_hash
        id2 = registry.get_id(doc2)

        assert hash1 != hash2
        assert id1.full_hash != id2.full_hash
        # Doc1 should not be in the new index
        with pytest.raises(KeyError):
            registry.get_id(doc1)

    def test_initialize_requires_children_attribute(self) -> None:
        """initialize() should raise TypeError for non-document types."""
        registry = NodeRegistry()

        with pytest.raises(TypeError, match="Expected TypstDocument root"):
            registry.initialize(TypstParagraph(text="Not a document"))  # type: ignore


class TestNodeRegistryCaching:
    """Test NodeID caching behavior."""

    def test_get_id_returns_cached_on_subsequent_calls(self) -> None:
        """get_id() should return cached NodeID on subsequent calls."""
        para = TypstParagraph(text="Test")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        id1 = registry.get_id(para)
        id2 = registry.get_id(para)

        assert id1 is id2  # Same object, cached

    def test_cache_uses_object_identity(self) -> None:
        """Cache should use id(node) as key, not content equality."""
        para1 = TypstParagraph(text="Same text")
        para2 = TypstParagraph(text="Same text")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para1, para2],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        id1 = registry.get_id(para1)
        id2 = registry.get_id(para2)

        assert id1 is not id2  # Different objects
        assert id1.node_hash == id2.node_hash  # But same content hash

    def test_get_id_raises_if_not_initialized(self) -> None:
        """get_id() should raise KeyError if initialize() not called."""
        para = TypstParagraph(text="Test")
        registry = NodeRegistry()

        with pytest.raises(KeyError, match="Did you call initialize"):
            registry.get_id(para)

    def test_get_id_raises_if_node_not_in_index(self) -> None:
        """get_id() should raise KeyError for unknown nodes."""
        para_in_doc = TypstParagraph(text="In doc")
        para_outside = TypstParagraph(text="Outside")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para_in_doc],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        # This should work
        registry.get_id(para_in_doc)

        # This should fail
        with pytest.raises(KeyError, match="not found in path index"):
            registry.get_id(para_outside)


class TestNodeRegistryNodeTypes:
    """Test handling of all 11 node types in path index."""

    def test_all_node_types_in_path_index(self) -> None:
        """_build_path_index() should handle all 11 node types."""
        # Create document with all node types
        heading = TypstHeading(text="Title")
        para = TypstParagraph(text="Paragraph")
        table = TypstTable(
            headers=["A", "B"],
            data=[["1", "2"]],
        )
        figure = TypstFigure(content="image.png", caption="A figure")
        equation = TypstEquation(latex="E=mc^2", display=True)
        code_block = TypstCodeBlock(text="print('hello')", language="python")
        raw_block = TypstRawBlock(format="html", text="<br/>")
        bullet_list = TypstBulletList(items=[[TypstParagraph(text="Item")]])
        ordered_list = TypstOrderedList(
            items=[[TypstParagraph(text="First")]],
            start=1,
        )
        section = TypstSection(
            heading=TypstHeading(text="Section"),
            body=[TypstParagraph(text="Section content")],
            subsections=[],
        )

        wrapper = TypstSection(
            heading=TypstHeading(text="Content"),
            body=[
                heading,
                para,
                table,
                figure,
                equation,
                code_block,
                raw_block,
                bullet_list,
                ordered_list,
            ],
            subsections=[],
        )
        doc = TypstDocument(children=[wrapper, section])

        registry = NodeRegistry()
        registry.initialize(doc)

        # Verify all top-level nodes are indexed
        assert "doc.children.0[TypstSection]" in registry.path_index  # wrapper
        assert "doc.children.0[TypstSection].body.0[TypstHeading]" in registry.path_index  # heading
        assert "doc.children.0[TypstSection].body.1[TypstParagraph]" in registry.path_index  # para
        assert "doc.children.0[TypstSection].body.2[TypstTable]" in registry.path_index  # table
        assert "doc.children.0[TypstSection].body.3[TypstFigure]" in registry.path_index  # figure
        assert "doc.children.0[TypstSection].body.4[TypstEquation]" in registry.path_index  # equation
        assert "doc.children.0[TypstSection].body.5[TypstCodeBlock]" in registry.path_index  # code_block
        assert "doc.children.0[TypstSection].body.6[TypstRawBlock]" in registry.path_index  # raw_block
        assert "doc.children.0[TypstSection].body.7[TypstBulletList]" in registry.path_index  # bullet_list
        assert "doc.children.0[TypstSection].body.8[TypstOrderedList]" in registry.path_index  # ordered_list
        assert "doc.children.1[TypstSection]" in registry.path_index  # section

    def test_section_heading_indexed(self) -> None:
        """Section heading should be indexed separately."""
        heading = TypstHeading(text="Section")
        section = TypstSection(
            heading=heading,
            body=[TypstParagraph(text="Content")],
            subsections=[],
        )
        doc = TypstDocument(children=[section])

        registry = NodeRegistry()
        registry.initialize(doc)

        assert "doc.children.0[TypstSection]" in registry.path_index  # section
        assert "doc.children.0[TypstSection].heading[TypstHeading]" in registry.path_index  # heading
        assert "doc.children.0[TypstSection].body.0[TypstParagraph]" in registry.path_index  # para

    def test_bullet_list_items_indexed(self) -> None:
        """Bullet list items should be indexed with nested blocks."""
        para1 = TypstParagraph(text="Item 1")
        para2 = TypstParagraph(text="Item 2")
        bullet_list = TypstBulletList(
            items=[
                [para1],
                [para2],
            ]
        )
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[bullet_list],
                subsections=[],
            ),
        ])

        registry = NodeRegistry()
        registry.initialize(doc)

        assert "doc.children.0[TypstSection].body.0[TypstBulletList]" in registry.path_index  # bullet_list
        assert "doc.children.0[TypstSection].body.0[TypstBulletList].items.0.0[TypstParagraph]" in registry.path_index  # para1
        assert "doc.children.0[TypstSection].body.0[TypstBulletList].items.1.0[TypstParagraph]" in registry.path_index  # para2

    def test_ordered_list_items_indexed(self) -> None:
        """Ordered list items should be indexed with nested blocks."""
        para1 = TypstParagraph(text="First")
        para2 = TypstParagraph(text="Second")
        ordered_list = TypstOrderedList(
            items=[
                [para1],
                [para2],
            ],
            start=1,
        )
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[ordered_list],
                subsections=[],
            ),
        ])

        registry = NodeRegistry()
        registry.initialize(doc)

        assert "doc.children.0[TypstSection].body.0[TypstOrderedList]" in registry.path_index  # ordered_list
        assert "doc.children.0[TypstSection].body.0[TypstOrderedList].items.0.0[TypstParagraph]" in registry.path_index  # para1
        assert "doc.children.0[TypstSection].body.0[TypstOrderedList].items.1.0[TypstParagraph]" in registry.path_index  # para2

    def test_nested_sections(self) -> None:
        """Nested sections should be indexed correctly."""
        inner_heading = TypstHeading(text="Inner")
        inner_section = TypstSection(
            heading=inner_heading,
            body=[TypstParagraph(text="Inner content")],
            subsections=[],
        )
        outer_heading = TypstHeading(text="Outer")
        outer_section = TypstSection(
            heading=outer_heading,
            body=[],
            subsections=[inner_section],
        )
        doc = TypstDocument(children=[outer_section])

        registry = NodeRegistry()
        registry.initialize(doc)

        assert "doc.children.0[TypstSection]" in registry.path_index  # outer_section
        assert "doc.children.0[TypstSection].heading[TypstHeading]" in registry.path_index  # outer_heading
        assert "doc.children.0[TypstSection].subsections.0[TypstSection]" in registry.path_index  # inner_section
        assert "doc.children.0[TypstSection].subsections.0[TypstSection].heading[TypstHeading]" in registry.path_index  # inner_heading


class TestNodeRegistryNodeIDs:
    """Test NodeID structure and properties."""

    def test_nodeid_has_path_fullhash_nodehash(self) -> None:
        """NodeID should have path, full_hash, and node_hash."""
        para = TypstParagraph(text="Test")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        node_id = registry.get_id(para)

        assert isinstance(node_id, NodeID)
        assert node_id.path == "doc.children.0[TypstSection].body.0[TypstParagraph]"
        assert node_id.full_hash == registry.full_hash
        assert len(node_id.node_hash) == 64  # SHA-256 hex digest

    def test_nodeid_canonical_format(self) -> None:
        """NodeID canonical should be path:full_hash:node_hash."""
        para = TypstParagraph(text="Test")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        node_id = registry.get_id(para)
        canonical = node_id.canonical

        expected = f"{node_id.path}:{node_id.full_hash}:{node_id.node_hash}"
        assert canonical == expected

    def test_different_nodes_different_nodehash(self) -> None:
        """Different content should produce different node_hash."""
        para1 = TypstParagraph(text="First")
        para2 = TypstParagraph(text="Second")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para1, para2],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        id1 = registry.get_id(para1)
        id2 = registry.get_id(para2)

        assert id1.full_hash == id2.full_hash  # Same document
        assert id1.node_hash != id2.node_hash  # Different content

    def test_same_content_same_nodehash(self) -> None:
        """Same content should produce same node_hash."""
        para1 = TypstParagraph(text="Same")
        para2 = TypstParagraph(text="Same")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para1, para2],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        id1 = registry.get_id(para1)
        id2 = registry.get_id(para2)

        assert id1.node_hash == id2.node_hash


class TestNodeRegistryHashComputation:
    """Test document and node hash computation."""

    def test_full_hash_deterministic(self) -> None:
        """Full hash should be deterministic for same document."""
        doc1 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Test")],
                subsections=[],
            ),
        ])
        doc2 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Test")],
                subsections=[],
            ),
        ])

        registry1 = NodeRegistry()
        registry1.initialize(doc1)

        registry2 = NodeRegistry()
        registry2.initialize(doc2)

        assert registry1.full_hash == registry2.full_hash

    def test_full_hash_different_for_different_docs(self) -> None:
        """Full hash should differ for different documents."""
        doc1 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="First")],
                subsections=[],
            ),
        ])
        doc2 = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Second")],
                subsections=[],
            ),
        ])

        registry1 = NodeRegistry()
        registry1.initialize(doc1)

        registry2 = NodeRegistry()
        registry2.initialize(doc2)

        assert registry1.full_hash != registry2.full_hash

    def test_node_hash_deterministic(self) -> None:
        """Node hash should be deterministic for same content."""
        para = TypstParagraph(text="Test")
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[para],
                subsections=[],
            ),
        ])

        registry1 = NodeRegistry()
        registry1.initialize(doc)

        registry2 = NodeRegistry()
        registry2.initialize(doc)

        id1 = registry1.get_id(para)
        id2 = registry2.get_id(para)

        assert id1.node_hash == id2.node_hash


class TestNodeRegistryEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_document(self) -> None:
        """Registry should handle empty document."""
        doc = TypstDocument(children=[])
        registry = NodeRegistry()
        registry.initialize(doc)

        assert registry.full_hash != ""
        assert "doc" in registry.path_index
        assert len(registry.path_index) == 1  # Just the document

    def test_deeply_nested_structure(self) -> None:
        """Registry should handle deeply nested structures."""
        # Create deeply nested section
        inner = TypstSection(
            heading=TypstHeading(text="Level 3"),
            body=[TypstParagraph(text="Deep")],
            subsections=[],
        )
        middle = TypstSection(
            heading=TypstHeading(text="Level 2"),
            body=[],
            subsections=[inner],
        )
        outer = TypstSection(
            heading=TypstHeading(text="Level 1"),
            body=[],
            subsections=[middle],
        )
        doc = TypstDocument(children=[outer])

        registry = NodeRegistry()
        registry.initialize(doc)

        # Verify all levels are indexed
        assert "doc.children.0[TypstSection]" in registry.path_index
        assert "doc.children.0[TypstSection].subsections.0[TypstSection]" in registry.path_index
        assert "doc.children.0[TypstSection].subsections.0[TypstSection].subsections.0[TypstSection]" in registry.path_index

    def test_list_with_multiple_blocks_per_item(self) -> None:
        """Registry should handle list items with multiple blocks."""
        para1 = TypstParagraph(text="First para")
        para2 = TypstParagraph(text="Second para")
        bullet_list = TypstBulletList(
            items=[
                [para1, para2],  # Two blocks in one item
            ]
        )
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[bullet_list],
                subsections=[],
            ),
        ])

        registry = NodeRegistry()
        registry.initialize(doc)

        assert "doc.children.0[TypstSection].body.0[TypstBulletList].items.0.0[TypstParagraph]" in registry.path_index  # para1
        assert "doc.children.0[TypstSection].body.0[TypstBulletList].items.0.1[TypstParagraph]" in registry.path_index  # para2

    def test_document_itself_can_have_id(self) -> None:
        """Document root can also have a NodeID."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Content"),
                body=[TypstParagraph(text="Test")],
                subsections=[],
            ),
        ])
        registry = NodeRegistry()
        registry.initialize(doc)

        doc_id = registry.get_id(doc)

        assert doc_id.path == "doc"
        assert doc_id.full_hash == registry.full_hash
