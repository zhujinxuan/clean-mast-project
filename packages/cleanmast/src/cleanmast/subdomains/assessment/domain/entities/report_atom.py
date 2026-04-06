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
from typing import Generic, Literal, Protocol, Self, TypeVar, overload

import dataframely as dy
import polars as pl


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
M = TypeVar("M")


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

    @abstractmethod
    def renderTable(self) -> str:
        """Render as Typst/markdown table.

        Returns:
            A string representation of the data as a table
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
    def renderSummary(self) -> str:
        """Render as text summary/paragraph.

        Returns:
            A text summary suitable for inclusion in a report
        """
        pass

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> str:
        """Generate image AND return Typst figure code with caption.

        This method combines image generation with Typst figure markup,
        automatically extracting caption and width from metadata.

        Args:
            output_dir: Directory where the image should be saved
            force: If True, regenerate even if file exists

        Returns:
            Typst figure markup string with embedded image reference
        """
        image_path = self.renderImage(output_dir, force)
        rel_path = image_path.relative_to(output_dir.parent)
        hashkey = self.get_or_compute_df_hashkey()
        caption = getattr(self.meta, "caption", "Figure")
        width = getattr(self.meta, "width", "80%")

        return f"""#figure(
  image("{rel_path.as_posix()}", width: {width}),
  caption: [{caption}],
) <fig-{hashkey}>
"""

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
