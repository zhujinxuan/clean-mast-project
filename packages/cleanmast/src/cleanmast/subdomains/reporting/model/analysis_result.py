from dataclasses import dataclass
from typing import Generic, TypeVar

import dataframely as dy
import polars as pl

from cleanmast.subdomains.reporting.model.analysis_metadata import AnalysisMetadata

Schema = TypeVar("Schema", bound=dy.Schema)


@dataclass(frozen=True)
class AnalysisResult(Generic[Schema]):
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
        validated = schema.validate(data, cast=True)
        return cls(data=validated, schema=schema, metadata=metadata)
