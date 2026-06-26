"""TypstRenderer for rendering reports to Typst format.

Provides helper methods for generating consistent Typst markup for
document preamble, sections, figures, tables, and text elements.

Key: Uses path.as_posix() not str(path) for Path-to-string conversion.
"""

from pathlib import Path


class TypstRenderer:
    """Renders reports to Typst format.

    Provides helper methods for generating consistent Typst markup for
    document preamble, sections, figures, tables, and text elements.

    Example:
        >>> renderer = TypstRenderer()
        >>> preamble = renderer.render_preamble("Monthly Wind Report")
        >>> section = renderer.render_section_header("Wind Rose Analysis")
        >>> figure = renderer.render_figure("images/chart.png", "Wind Chart", "fig-wind")
        >>> print(preamble + section + figure)
    """

    @staticmethod
    def render_preamble(title: str) -> str:
        """Render Typst document preamble with Chinese font support.

        Sets up the document with Chinese fonts (Linux Libertine + Source Han Serif SC)
        and configures heading numbering.

        Args:
            title: The document title to include in the preamble.

        Returns:
            Typst markup string with document setup.

        Example:
            >>> renderer = TypstRenderer()
            >>> print(renderer.render_preamble("Report"))
            #set text(font: ("Linux Libertine", "Source Han Serif SC"))
            #set heading(numbering: "1.")
            ...
        """
        return f'''#set text(font: ("Linux Libertine", "Source Han Serif SC"))
#set heading(numbering: "1.")

= {title}

'''

    @staticmethod
    def render_section_header(title: str) -> str:
        """Render a section heading.

        Args:
            title: The section title.

        Returns:
            Typst section heading markup.

        Example:
            >>> renderer = TypstRenderer()
            >>> print(renderer.render_section_header("Data Cleaning"))
            == Data Cleaning

        """
        return f"== {title}\n\n"

    @staticmethod
    def render_figure(
        image_path: str, caption: str, label: str, width: str = "80%"
    ) -> str:
        """Render a figure with image, caption, and label.

        Args:
            image_path: Path to the image file (relative to Typst document).
            caption: Figure caption text.
            label: Figure label for referencing (e.g., "fig-wind").
            width: Image width as Typst length (default: "80%").

        Returns:
            Typst figure markup.

        Example:
            >>> renderer = TypstRenderer()
            >>> print(renderer.render_figure("images/chart.png", "Wind Chart", "fig-wind"))
            #figure(
              image("images/chart.png", width: 80%),
              caption: [Wind Chart],
            ) <fig-wind>
        """
        return f'''#figure(
  image("{image_path}", width: {width}),
  caption: [{caption}],
) <{label}>

'''

    @staticmethod
    def render_table(table_markup: str) -> str:
        """Render a table, validating the markup is valid Typst.

        This method primarily serves as a pass-through that validates the
        table markup starts with the expected Typst table syntax.

        Args:
            table_markup: Raw Typst table markup string.

        Returns:
            The validated table markup.

        Raises:
            ValueError: If table_markup does not start with valid Typst table syntax.

        Example:
            >>> renderer = TypstRenderer()
            >>> table = '#table(columns: (auto,), [Cell])'
            >>> print(renderer.render_table(table))
            #table(columns: (auto,), [Cell])
        """
        stripped = table_markup.strip()
        if not stripped.startswith("#table("):
            raise ValueError(
                f"Invalid Typst table markup: must start with '#table(', "
                f"got: {stripped[:50]}..."
            )
        return table_markup + "\n\n"

    @staticmethod
    def render_summary(text: str) -> str:
        """Render a summary paragraph.

        Args:
            text: The summary text content.

        Returns:
            Typst paragraph markup.

        Example:
            >>> renderer = TypstRenderer()
            >>> print(renderer.render_summary("Analysis result summary."))
            Analysis result summary.

        """
        return f"{text}\n\n"

    @staticmethod
    def render_reference(label: str) -> str:
        """Render a reference to a labeled element.

        Args:
            label: The label to reference (e.g., "fig-abc123").

        Returns:
            Typst reference markup.

        Example:
            >>> renderer = TypstRenderer()
            >>> print(renderer.render_reference("fig-wind"))
            @fig-wind
        """
        return f"@{label}"

    @classmethod
    def render_figure_from_path(
        cls,
        image_path: Path,
        caption: str,
        label: str,
        width: str = "80%",
        relative_to: Path | None = None,
    ) -> str:
        """Render a figure with a Path object for the image.

        Convenience method that converts Path to POSIX string for Typst.

        Args:
            image_path: Path to the image file.
            caption: Figure caption text.
            label: Figure label for referencing.
            width: Image width as Typst length (default: "80%").
            relative_to: If provided, compute relative path from this directory.

        Returns:
            Typst figure markup.

        Example:
            >>> renderer = TypstRenderer()
            >>> path = Path("report/images/chart.png")
            >>> print(renderer.render_figure_from_path(path, "Chart", "fig-1"))
            #figure(
              image("report/images/chart.png", width: 80%),
              caption: [Chart],
            ) <fig-1>
        """
        if relative_to is not None:
            try:
                rel_path = image_path.relative_to(relative_to)
                path_str = rel_path.as_posix()
            except ValueError:
                path_str = image_path.as_posix()
        else:
            path_str = image_path.as_posix()

        return cls.render_figure(path_str, caption, label, width)
