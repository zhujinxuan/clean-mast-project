"""Tests for TypstRenderer."""


import pytest
from cleanmast.subdomains.assessment.infrastructure import TypstRenderer


class TestTypstRendererRenderPreamble:
    def test_render_preamble_includes_fonts(self):
        result = TypstRenderer.render_preamble("Test Title")

        assert "Linux Libertine" in result
        assert "Source Han Serif SC" in result

    def test_render_preamble_includes_heading_numbering(self):
        result = TypstRenderer.render_preamble("Test Title")

        assert 'heading(numbering: "1.")' in result

    def test_render_preamble_includes_title(self):
        result = TypstRenderer.render_preamble("My Report")

        assert "= My Report" in result


class TestTypstRendererRenderSectionHeader:
    def test_render_section_header_level2(self):
        result = TypstRenderer.render_section_header("Analysis")

        assert result.startswith("== ")

    def test_render_section_header_includes_title(self):
        result = TypstRenderer.render_section_header("Wind Speed Analysis")

        assert "Wind Speed Analysis" in result


class TestTypstRendererRenderFigure:
    def test_render_figure_includes_image(self):
        result = TypstRenderer.render_figure(
            "images/chart.png", "Chart Caption", "fig-chart"
        )

        assert "image(" in result
        assert 'images/chart.png"' in result

    def test_render_figure_includes_caption(self):
        result = TypstRenderer.render_figure(
            "images/chart.png", "My Caption", "fig-chart"
        )

        assert "caption: [My Caption]" in result

    def test_render_figure_includes_label(self):
        result = TypstRenderer.render_figure(
            "images/chart.png", "Caption", "fig-wind-speed"
        )

        assert "<fig-wind-speed>" in result


class TestTypstRendererRenderTable:
    def test_render_table_valid_markup(self):
        table_markup = '#table(columns: (auto,), [Cell])'
        result = TypstRenderer.render_table(table_markup)

        assert table_markup in result

    def test_render_table_invalid_markup_raises(self):
        with pytest.raises(ValueError, match="Invalid Typst table markup"):
            TypstRenderer.render_table("not a table")


class TestTypstRendererRenderSummary:
    def test_render_summary_includes_text(self):
        result = TypstRenderer.render_summary("This is a summary.")

        assert "This is a summary." in result


class TestTypstRendererRenderReference:
    def test_render_reference_format(self):
        result = TypstRenderer.render_reference("fig-wind-speed")

        assert result == "@fig-wind-speed"
