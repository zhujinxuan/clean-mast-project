from dataclasses import dataclass
from typing import Generic, TypeVar

import dataframely as dy
import polars as pl

from .analysis_metadata import AnalysisMetadata

Schema = TypeVar("Schema", bound=dy.Schema)


@dataclass(frozen=True)
class AnalysisResult(Generic[Schema]):
    """Result of an analysis operation with typed schema."""

    data: pl.DataFrame
    schema: type[Schema]
    metadata: AnalysisMetadata

    @classmethod
    def create(
        cls,
        schema: type[Schema],
        data: pl.DataFrame,
        metadata: AnalysisMetadata,
    ) -> "AnalysisResult[Schema]":
        """Factory method that validates data against schema."""
        # Validate and cast to schema
        validated = schema.validate(data, cast=True)
        return cls(data=validated, schema=schema, metadata=metadata)
