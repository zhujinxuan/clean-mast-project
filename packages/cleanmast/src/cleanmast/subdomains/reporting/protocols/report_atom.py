"""ReportAtom base class for content-addressable report components."""

from __future__ import annotations

import hashlib
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Literal, Protocol, Self, TypeVar, overload

import polars as pl
from typst_ir import TypstFigure

if TYPE_CHECKING:
    import dataframely as dy
    from typst_ir import TypstParagraph, TypstTable


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
    ) -> "dy.DataFrame": ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: Literal[False],
    ) -> "dy.LazyFrame": ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: bool,
    ) -> "dy.DataFrame | dy.LazyFrame": ...


T = TypeVar("T", bound=SchemaProtocol)


M = TypeVar("M")


@dataclass(frozen=True)
class ReportAtom(ABC, Generic[T, M]):
    """Base class for all report atoms with content-addressable caching.

    Report atoms are the fundamental building blocks of reports. Each atom
    contains a validated DataFrame, a schema for validation, and metadata.
    The content hash is computed once during construction and stored in an
    immutable field, avoiding the mutable cached state used by assessment.

    Type Parameters:
        T: The schema type used for validation (e.g., a dataframely Schema)
        M: The metadata type containing display properties (caption, width, etc.)
    """

    df: pl.DataFrame
    schema: type[T]
    meta: M
    _df_hashkey: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Compute and freeze the content hash after construction."""
        hashkey = self._compute_df_hashkey()
        object.__setattr__(self, "_df_hashkey", hashkey)

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
        return cls(df=validated, schema=schema, meta=meta)

    def _compute_df_hashkey(self) -> str:
        """Compute content hash from DataFrame parquet serialization.

        The hash is derived from the Parquet serialization of the DataFrame
        to ensure content-addressability. The first 12 characters of SHA256
        are used for brevity while maintaining sufficient uniqueness.

        Returns:
            A string in the format "{ClassName}_{hash}" for referencing
        """
        buf = io.BytesIO()
        self.df.write_parquet(buf)
        content_hash = hashlib.sha256(buf.getvalue()).hexdigest()[:12]
        atom_type = self.__class__.__name__
        return f"{atom_type}_{content_hash}"

    def get_or_compute_df_hashkey(self) -> str:
        """Get the precomputed content hash.

        Returns:
            A string in the format "{ClassName}_{hash}" for referencing
        """
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
    def renderTable(self) -> "TypstTable | None":
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
    def renderSummary(self) -> 'list["TypstParagraph"]':
        """Render as TypstParagraph IR node.

        Returns:
            A list containing a TypstParagraph IR node with the summary text
        """
        pass

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> "TypstFigure | None":
        """Generate image AND return TypstFigure IR node.

        This method combines image generation with Typst figure IR node creation,
        using the atom's default caption.

        Args:
            output_dir: Directory where the image should be saved
            force: If True, regenerate even if file exists

        Returns:
            A TypstFigure IR node, or None if no image was generated
        """
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
