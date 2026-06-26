"""ReportAtom base class for content-addressable report components.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-001-aggregates
Compliance: Subdomain layout ✓ | Aggregate ✓ | Report Pattern ✓
"""

from __future__ import annotations

import hashlib
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Literal, Protocol, Self, TypeVar, overload

import dataframely as dy
import polars as pl

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.shared.ir_types import (
        TypstFigure,
        TypstParagraph,
        TypstTable,
    )


class SchemaProtocol(Protocol):
    """Protocol for schema classes that can validate DataFrames.
    
    Matches dataframely.Schema.validate signature for compatibility.
    """

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: Literal[True] = True,
    ) -> dy.DataFrame: ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: Literal[False],
    ) -> dy.LazyFrame: ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: bool,
    ) -> dy.DataFrame | dy.LazyFrame: ...


T = TypeVar("T", bound=SchemaProtocol)


class MetaWithCaption(Protocol):
    """Protocol for metadata objects that provide a caption."""

    caption: str | None


M = TypeVar("M", bound=MetaWithCaption)


@dataclass
class ReportAtom(ABC, Generic[T, M]):
    """Base class for all report atoms with content-addressable caching.

    Report atoms are the fundamental building blocks of reports. Each atom
    contains a validated DataFrame, a schema for validation, and metadata.
    The content hash is computed lazily and cached for efficient reference
    generation and caching.

    Type Parameters:
        T: The schema type used for validation (e.g., a dataframely Schema)
        M: The metadata type containing display properties (caption, width, etc.)
    """

    df: pl.DataFrame
    schema: type[T]
    meta: M
    _df_hashkey: str | None = field(default=None, repr=False)

    @classmethod
    def create(cls, schema: type[T], df: pl.DataFrame, meta: M) -> Self:
        """Factory: validates once, returns typed atom.

        Args:
            schema: The schema class to validate against
            df: The DataFrame to validate and store
            meta: Metadata object with display properties

        Returns:
            A new ReportAtom instance with validated data
        """
        validated = schema.validate(df, cast=True)
        instance = cls.__new__(cls)
        instance.df = validated
        instance.schema = schema
        instance.meta = meta
        instance._df_hashkey = None
        return instance

    def get_or_compute_df_hashkey(self) -> str:
        """Get content hash - computes once, caches forever.

        The hash is computed from the Parquet serialization of the DataFrame
        to ensure content-addressability. The first 12 characters of SHA256
        are used for brevity while maintaining sufficient uniqueness.

        Returns:
            A string in the format "{ClassName}_{hash}" for referencing
        """
        if self._df_hashkey is None:
            buf = io.BytesIO()
            self.df.write_parquet(buf)
            content_hash = hashlib.sha256(buf.getvalue()).hexdigest()[:12]
            atom_type = self.__class__.__name__
            self._df_hashkey = f"{atom_type}_{content_hash}"
        return self._df_hashkey

    @property
    def default_image_caption(self) -> str | None:
        """Default caption for images rendered by this atom."""
        return None

    @property
    def default_table_caption(self) -> str | None:
        """Default caption for tables rendered by this atom."""
        return None

    @abstractmethod
    def renderTable(self) -> "TypstTable" | None:
        """Render as TypstTable IR node.

        Returns:
            A TypstTable IR node, or None if this atom does not render a table
        """
        pass

    @abstractmethod
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate image file, return path.

        Args:
            output_dir: Directory where the image should be saved
            force: If True, regenerate even if file exists

        Returns:
            Path to the generated image file
        """
        pass

    @abstractmethod
    def renderSummary(self) -> list["TypstParagraph"]:
        """Render as TypstParagraph IR node.

        Returns:
            A list containing a TypstParagraph IR node with the summary text
        """
        pass

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> "TypstFigure" | None:
        """Generate image AND return TypstFigure IR node.

        This method combines image generation with Typst figure IR node creation,
        using the atom's default caption.

        Args:
            output_dir: Directory where the image should be saved
            force: If True, regenerate even if file exists

        Returns:
            A TypstFigure IR node, or None if no image was generated
        """
        from cleanmast.subdomains.assessment.shared.ir_types import TypstFigure

        image_path = self.renderImage(output_dir, force)
        if not image_path or not image_path.name or image_path == output_dir:
            return None
        rel_path = image_path.relative_to(output_dir.parent)
        caption = self.default_image_caption or "Figure"

        return TypstFigure(content=rel_path.as_posix(), caption=caption)

    def getReference(self) -> str:
        """Get Typst reference string.

        Returns:
            A Typst reference in the format "@fig-{hashkey}"
        """
        return f"@fig-{self.get_or_compute_df_hashkey()}"

    def getTableReference(self) -> str:
        """Get Typst table reference string.

        Returns:
            A Typst reference in the format "@tbl-{hashkey}"
        """
        return f"@tbl-{self.get_or_compute_df_hashkey()}"
