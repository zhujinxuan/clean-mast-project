"""Tests for TypstRenderer."""

from pathlib import Path

import pytest

from cleanmast.report.renderer import TypstRenderer


class TestTypstRendererRenderPreamble:
    """Tests for TypstRenderer.render_preamble method."""

    def test_render_preamble_includes_fonts(self):
        """Test that preamble includes Chinese font configuration."""
        result = TypstRenderer.render_preamble("Test Title")

        assert "Linux Libertine" in result
        assert "Source Han Serif SC" in result

    def test_render_preamble_includes_heading_numbering(self):
        """Test that preamble includes heading numbering."""
        result = TypstRenderer.render_preamble("Test Title")

        assert 'heading(numbering: "1.")' in result

    def test_render_preamble_includes_title(self):
        """Test that preamble includes the document title."""
        result = TypstRenderer.render_preamble("My Report")

        assert "= My Report" in result

    def test_render_preamble_chinese_title(self):
        """Test that preamble handles Chinese titles."""
        result = TypstRenderer.render_preamble("测风塔分析报告")

        assert "= 测风塔分析报告" in result

    def test_render_preamble_returns_string(self):
        """Test that render_preamble returns a string."""
        result = TypstRenderer.render_preamble("Test")

        assert isinstance(result, str)

    def test_render_preamble_structure(self):
        """Test that preamble has correct structure."""
        result = TypstRenderer.render_preamble("Test")

        lines = result.strip().split("\n")
        assert lines[0] == '#set text(font: ("Linux Libertine", "Source Han Serif SC"))'
        assert lines[1] == '#set heading(numbering: "1.")'


class TestTypstRendererRenderSectionHeader:
    """Tests for TypstRenderer.render_section_header method."""

    def test_render_section_header_level2(self):
        """Test that section header uses level 2 heading."""
        result = TypstRenderer.render_section_header("Analysis")

        assert result.startswith("== ")

    def test_render_section_header_includes_title(self):
        """Test that section header includes the title."""
        result = TypstRenderer.render_section_header("Wind Speed Analysis")

        assert "Wind Speed Analysis" in result

    def test_render_section_header_chinese(self):
        """Test that section header handles Chinese text."""
        result = TypstRenderer.render_section_header("月平均风速分析")

        assert "== 月平均风速分析" in result

    def test_render_section_header_includes_newlines(self):
        """Test that section header includes trailing newlines."""
        result = TypstRenderer.render_section_header("Test")

        assert result.endswith("\n\n")


class TestTypstRendererRenderFigure:
    """Tests for TypstRenderer.render_figure method."""

    def test_render_figure_includes_image(self):
        """Test that figure includes image reference."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "Chart Caption", "fig-chart"
        )

        assert "image(" in result
        assert 'images/chart.png"' in result

    def test_render_figure_includes_caption(self):
        """Test that figure includes caption."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "My Caption", "fig-chart"
        )

        assert "caption: [My Caption]" in result

    def test_render_figure_includes_label(self):
        """Test that figure includes label."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "Caption", "fig-wind-speed"
        )

        assert "<fig-wind-speed>" in result

    def test_render_figure_default_width(self):
        """Test that figure uses default width of 80%."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "Caption", "fig-test"
        )

        assert "width: 80%" in result

    def test_render_figure_custom_width(self):
        """Test that figure accepts custom width."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "Caption", "fig-test", width="70%"
        )

        assert "width: 70%" in result

    def test_render_figure_structure(self):
        """Test that figure has correct Typst structure."""
        result = TypstRenderer.render_figure(
            "images/chart.png", "Caption", "fig-test"
        )

        assert result.startswith("#figure(")
        assert result.strip().endswith(") <fig-test>")


class TestTypstRendererRenderTable:
    """Tests for TypstRenderer.render_table method."""

    def test_render_table_valid_markup(self):
        """Test that valid table markup is returned unchanged."""
        table_markup = '#table(columns: (auto,), [Cell])'
        result = TypstRenderer.render_table(table_markup)

        assert table_markup in result

    def test_render_table_adds_newlines(self):
        """Test that table adds trailing newlines."""
        table_markup = '#table(columns: (auto,), [Cell])'
        result = TypstRenderer.render_table(table_markup)

        assert result.endswith("\n\n")

    def test_render_table_invalid_markup_raises(self):
        """Test that invalid table markup raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Typst table markup"):
            TypstRenderer.render_table("not a table")

    def test_render_table_invalid_markup_detail(self):
        """Test that error message includes the invalid markup."""
        with pytest.raises(ValueError) as exc_info:
            TypstRenderer.render_table("invalid markup here")

        assert "#table(" in str(exc_info.value)

    def test_render_table_strips_whitespace(self):
        """Test that table markup is stripped before validation."""
        table_markup = '  #table(columns: (auto,), [Cell])  '
        result = TypstRenderer.render_table(table_markup)

        assert "#table(" in result


class TestTypstRendererRenderSummary:
    """Tests for TypstRenderer.render_summary method."""

    def test_render_summary_includes_text(self):
        """Test that summary includes the text content."""
        result = TypstRenderer.render_summary("This is a summary.")

        assert "This is a summary." in result

    def test_render_summary_chinese_text(self):
        """Test that summary handles Chinese text."""
        result = TypstRenderer.render_summary("这是分析结果总结。")

        assert "这是分析结果总结。" in result

    def test_render_summary_adds_newlines(self):
        """Test that summary adds trailing newlines."""
        result = TypstRenderer.render_summary("Test")

        assert result.endswith("\n\n")

    def test_render_summary_returns_string(self):
        """Test that render_summary returns a string."""
        result = TypstRenderer.render_summary("Test")

        assert isinstance(result, str)


class TestTypstRendererRenderReference:
    """Tests for TypstRenderer.render_reference method."""

    def test_render_reference_format(self):
        """Test that reference uses Typst format."""
        result = TypstRenderer.render_reference("fig-wind-speed")

        assert result == "@fig-wind-speed"

    def test_render_reference_starts_with_at(self):
        """Test that reference starts with @ symbol."""
        result = TypstRenderer.render_reference("fig-test")

        assert result.startswith("@")

    def test_render_reference_returns_string(self):
        """Test that render_reference returns a string."""
        result = TypstRenderer.render_reference("fig-test")

        assert isinstance(result, str)


class TestTypstRendererRenderFigureFromPath:
    """Tests for TypstRenderer.render_figure_from_path method."""

    def test_render_figure_from_path_converts_to_posix(self, tmp_path: Path):
        """Test that Path is converted to POSIX path."""
        image_path = tmp_path / "images" / "chart.png"

        result = TypstRenderer.render_figure_from_path(
            image_path, "Caption", "fig-test"
        )

        # Should use forward slashes (POSIX)
        assert "\\" not in result

    def test_render_figure_from_path_with_relative_to(self, tmp_path: Path):
        """Test computing relative path from base directory."""
        base_dir = tmp_path / "report"
        image_path = base_dir / "images" / "chart.png"

        result = TypstRenderer.render_figure_from_path(
            image_path, "Caption", "fig-test", relative_to=base_dir
        )

        # Should use relative path
        assert 'images/chart.png"' in result

    def test_render_figure_from_path_fallback_when_not_relative(
        self,
        tmp_path: Path,
    ):
        """Test fallback to absolute path when not relative to base."""
        image_path = Path("/some/other/path/chart.png")
        base_dir = tmp_path / "report"

        result = TypstRenderer.render_figure_from_path(
            image_path, "Caption", "fig-test", relative_to=base_dir
        )

        # Should still work even if not relative
        assert "chart.png" in result

    def test_render_figure_from_path_no_relative_to(self, tmp_path: Path):
        """Test without relative_to parameter."""
        image_path = tmp_path / "chart.png"

        result = TypstRenderer.render_figure_from_path(
            image_path, "Caption", "fig-test"
        )

        assert "chart.png" in result
        assert "#figure(" in result


class TestTypstRendererStaticMethods:
    """Tests for static method behavior."""

    def test_all_methods_are_static(self):
        """Test that all renderer methods can be called without instance."""
        # Should not require instantiation
        preamble = TypstRenderer.render_preamble("Test")
        section = TypstRenderer.render_section_header("Test")
        figure = TypstRenderer.render_figure("img.png", "Cap", "fig")
        table = TypstRenderer.render_table("#table(columns: (auto,), [Cell])")
        summary = TypstRenderer.render_summary("Test")
        reference = TypstRenderer.render_reference("fig-test")

        assert all([
            isinstance(preamble, str),
            isinstance(section, str),
            isinstance(figure, str),
            isinstance(table, str),
            isinstance(summary, str),
            isinstance(reference, str),
        ])

    def test_classmethod_render_figure_from_path(self):
        """Test that render_figure_from_path is a classmethod."""
        # Should be callable on class
        result = TypstRenderer.render_figure_from_path(
            Path("test.png"), "Caption", "fig-test"
        )
        assert isinstance(result, str)

        # Should be callable on instance too
        renderer = TypstRenderer()
        result = renderer.render_figure_from_path(
            Path("test.png"), "Caption", "fig-test"
        )
        assert isinstance(result, str)


class TestTypstRendererIntegration:
    """Integration tests for TypstRenderer."""

    def test_complete_document_structure(self):
        """Test generating a complete document structure."""
        preamble = TypstRenderer.render_preamble("测风塔分析报告")
        section1 = TypstRenderer.render_section_header("月平均风速")
        figure1 = TypstRenderer.render_figure(
            "images/wind-speed.png", "月平均风速图表", "fig-wind-speed"
        )
        table1 = TypstRenderer.render_table(
            '#table(columns: (auto, auto), [月份], [风速])'
        )
        summary1 = TypstRenderer.render_summary(
            "该图表显示了各月份的平均风速变化。"
        )
        reference1 = TypstRenderer.render_reference("fig-wind-speed")

        document = (
            preamble +
            section1 +
            figure1 +
            table1 +
            summary1 +
            f"详见 {reference1}。"
        )

        # Verify document contains all components
        assert "#set text(" in document
        assert "= 测风塔分析报告" in document
        assert "== 月平均风速" in document
        assert "#figure(" in document
        assert "#table(" in document
        assert "@fig-wind-speed" in document

    def test_typst_syntax_validity(self):
        """Test that generated Typst syntax appears valid."""
        figure = TypstRenderer.render_figure(
            "images/test.png", "Caption", "fig-test", "90%"
        )

        # Basic syntax checks
        assert figure.startswith("#figure(")
        assert 'image("' in figure
        assert "width:" in figure
        assert "caption:" in figure
        assert figure.strip().endswith(") <fig-test>")
