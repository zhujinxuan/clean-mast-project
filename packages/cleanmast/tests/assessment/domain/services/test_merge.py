"""Tests for paragraph merge utility."""

from cleanmast.subdomains.assessment.domain.services.utils.merge import (
    merge_paragraphs,
)
from typst_ir import TypstParagraph


class TestMergeParagraphs:
    """Tests for merge_paragraphs utility function."""

    def test_empty_list_returns_empty_paragraph(self):
        """Empty list should return a TypstParagraph with empty text."""
        result = merge_paragraphs([])

        assert isinstance(result, TypstParagraph)
        assert result.text == ""

    def test_single_paragraph_returns_as_is(self):
        """Single paragraph should be returned unchanged."""
        para = TypstParagraph(text="Hello")
        result = merge_paragraphs([para])

        assert result.text == "Hello"

    def test_multiple_paragraphs_joined_with_default_separator(self):
        """Multiple paragraphs should be joined with a space by default."""
        paragraphs = [
            TypstParagraph(text="Hello"),
            TypstParagraph(text="world"),
            TypstParagraph(text="!"),
        ]
        result = merge_paragraphs(paragraphs)

        assert result.text == "Hello world !"

    def test_custom_separator(self):
        """Custom separator should be used when provided."""
        paragraphs = [
            TypstParagraph(text="A"),
            TypstParagraph(text="B"),
        ]
        result = merge_paragraphs(paragraphs, sep=" - ")

        assert result.text == "A - B"

    def test_empty_text_paragraphs_are_skipped(self):
        """Paragraphs with empty text should be skipped."""
        paragraphs = [
            TypstParagraph(text="Hello"),
            TypstParagraph(text=""),
            TypstParagraph(text="world"),
        ]
        result = merge_paragraphs(paragraphs)

        assert result.text == "Hello world"

    def test_whitespace_only_paragraphs_are_skipped(self):
        """Paragraphs with whitespace-only text should be skipped."""
        paragraphs = [
            TypstParagraph(text="Hello"),
            TypstParagraph(text="   "),
            TypstParagraph(text="\t\n"),
            TypstParagraph(text="world"),
        ]
        result = merge_paragraphs(paragraphs)

        assert result.text == "Hello world"

    def test_mixed_empty_and_non_empty_paragraphs(self):
        """A mix of empty, whitespace-only, and real paragraphs."""
        paragraphs = [
            TypstParagraph(text=""),
            TypstParagraph(text="First"),
            TypstParagraph(text="  "),
            TypstParagraph(text="Second"),
            TypstParagraph(text="\n"),
            TypstParagraph(text="Third"),
        ]
        result = merge_paragraphs(paragraphs, sep=", ")

        assert result.text == "First, Second, Third"

    def test_all_empty_paragraphs_returns_empty(self):
        """If all paragraphs are empty/whitespace, return empty paragraph."""
        paragraphs = [
            TypstParagraph(text=""),
            TypstParagraph(text="   "),
            TypstParagraph(text="\t"),
        ]
        result = merge_paragraphs(paragraphs)

        assert result.text == ""

    def test_no_double_separators_when_skipping(self):
        """Skipped paragraphs should not create double separators."""
        paragraphs = [
            TypstParagraph(text="A"),
            TypstParagraph(text=""),
            TypstParagraph(text=""),
            TypstParagraph(text="B"),
        ]
        result = merge_paragraphs(paragraphs, sep="-")

        assert result.text == "A-B"
