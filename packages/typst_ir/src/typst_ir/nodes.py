"""Domain-level Typst IR types - Pydantic models for document elements.

Defines core IR nodes for representing Typst documents at the domain layer.
These types are pure data structures with no dependencies on infrastructure.

All nodes use frozen Pydantic BaseModels for safety, hashability, and validation.
"""

from __future__ import annotations

from typing import Annotated, Literal, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TypstTable(BaseModel):
    """Table node for tabular data.

    Represents a table with headers, data rows, and optional caption.

    Attributes:
        data: 2D list of strings representing table cells
        headers: List of column header strings
        caption: Optional table caption
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstTable"] = Field(default="TypstTable")

    data: list[list[str]]
    headers: list[str]
    caption: str | None = None


class TypstFigure(BaseModel):
    """Figure node for images and diagrams.

    Represents a figure with content reference and caption.

    Attributes:
        content: Path to image file or figure content
        caption: Figure caption text
        kind: Figure kind/type (default: "image")
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstFigure"] = Field(default="TypstFigure")

    content: str
    caption: str
    kind: str = "image"


class TypstHeading(BaseModel):
    """Heading node for section titles.

    Represents a heading with text. The level is derived from the
    document structure (e.g., nesting depth within sections).

    Attributes:
        text: Heading text content
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstHeading"] = Field(default="TypstHeading")

    text: str


class TypstParagraph(BaseModel):
    """Paragraph node for text content.

    Represents a plain text paragraph in the document.

    Attributes:
        text: Paragraph text content
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstParagraph"] = Field(default="TypstParagraph")

    text: str


class TypstEquation(BaseModel):
    """Equation node for LaTeX math content.

    Represents a mathematical equation that can be inline or display mode.

    Attributes:
        latex: LaTeX equation content
        display: Whether to render as display (block) equation (default: False for inline)
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstEquation"] = Field(default="TypstEquation")

    latex: str
    display: bool = False


class TypstCodeBlock(BaseModel):
    """Code block node for syntax-highlighted code.

    Represents a block of source code with optional language specification.

    Attributes:
        text: Code content
        language: Programming language for syntax highlighting (default: None)
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstCodeBlock"] = Field(default="TypstCodeBlock")

    text: str
    language: str | None = None


class TypstRawBlock(BaseModel):
    """Raw block node for unprocessed content.

    Represents raw content that should be passed through without processing.

    Attributes:
        format: Format identifier for the raw content
        text: Raw content text
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstRawBlock"] = Field(default="TypstRawBlock")

    format: str
    text: str


class TypstSection(BaseModel):
    """Section node for grouping content under a heading.

    Represents a document section containing a heading, body content blocks,
    and optional subsections. Sections can be nested to create hierarchical
    document structure.

    Attributes:
        heading: The section heading
        body: Content blocks within this section (excluding subsections)
        subsections: Nested sections within this section
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstSection"] = Field(default="TypstSection")

    heading: TypstHeading
    body: Sequence["TypstBodyBlock"]
    subsections: list["TypstSection"]

    @model_validator(mode="after")
    def _validate_body_and_subsections(self) -> "TypstSection":
        for item in self.body:
            if isinstance(item, TypstSection):
                raise ValueError(
                    "TypstSection found in body field — use subsections for nested sections"
                )
        for item in self.subsections:
            if not isinstance(item, TypstSection):
                raise ValueError(
                    "Non-section block found in subsections field — use body for content blocks"
                )
        return self


class TypstBulletList(BaseModel):
    """Bullet list node for unordered lists.

    Represents a bulleted list where each item can contain multiple blocks.

    Attributes:
        items: List of list items, where each item is a list of blocks
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstBulletList"] = Field(default="TypstBulletList")

    items: list[list["TypstBlock"]]


class TypstOrderedList(BaseModel):
    """Ordered list node for numbered lists.

    Represents a numbered list where each item can contain multiple blocks.

    Attributes:
        items: List of list items, where each item is a list of blocks
        start: Starting number for the list (default: 1)
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstOrderedList"] = Field(default="TypstOrderedList")

    items: list[list["TypstBlock"]]
    start: int = 1


# Type alias for all valid document child types (leaf nodes)
TypstChild = Annotated[
    Union[
        TypstTable,
        TypstFigure,
        TypstHeading,
        TypstParagraph,
        TypstEquation,
        TypstCodeBlock,
        TypstRawBlock,
    ],
    Field(discriminator="typst_type"),
]

TypstBodyBlock = Annotated[
    Union[
        TypstChild,
        TypstBulletList,
        TypstOrderedList,
    ],
    Field(discriminator="typst_type"),
]

# Type alias for all valid block-level content (includes sections and lists)
TypstBlock = Annotated[
    Union[
        TypstBodyBlock,
        TypstSection,
    ],
    Field(discriminator="typst_type"),
]


class TypstDocument(BaseModel):
    """Document node - root container for all content.

    Represents a complete Typst document containing a sequence
    of child nodes (tables, figures, headings, paragraphs, sections, lists).

    Attributes:
        children: Ordered list of child nodes
    """

    model_config = ConfigDict(frozen=True)
    typst_type: Literal["TypstDocument"] = Field(default="TypstDocument")

    children: list[TypstSection]
