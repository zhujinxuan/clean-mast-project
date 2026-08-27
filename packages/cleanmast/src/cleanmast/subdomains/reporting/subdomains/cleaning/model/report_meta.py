"""Metadata for cleaning report atoms."""

from dataclasses import dataclass, field

import polars as pl


@dataclass(frozen=True)
class CleaningAtomMeta:
    """Metadata for cleaning capability atoms.

    Attributes:
        mast_names: Masts contributing to the subsection.
        text: Placeholder line (Wave 1); real atoms carry their own stats.
    """

    mast_names: list[str] = field(default_factory=list)
    text: str = ""


@dataclass(frozen=True)
class CleaningRulesAtomMeta:
    """Metadata for the cleaning-rules table atom (2.3.3).

    Attributes:
        rules_source: Filename the rules were read from (e.g.
            "process-clean.toml"), for traceability.
    """

    rules_source: str = ""


@dataclass(frozen=True)
class CleaningViolationsAtomMeta:
    """Metadata for the violations table atom (2.3.3).

    Attributes:
        mast_names: Masts covered by the table (input order).
        summary_lines: One sentence per mast — totals with
            violation_percentage when present, or a missing-stats note.
    """

    mast_names: list[str] = field(default_factory=list)
    summary_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorrelationMatrixAtomMeta:
    """Metadata for the correlation-matrix table atom (2.3.5).

    Attributes:
        mast_name: Mast the matrix belongs to.
        labels: Ordered height labels — table row/column order.
        caption: Table caption text.
    """

    mast_name: str
    labels: list[str] = field(default_factory=list)
    caption: str = ""


@dataclass(frozen=True)
class ScatterRegressionAtomMeta:
    """Metadata for the scatter-regression figure atom (2.3.5–2.3.7).

    Attributes:
        caption: Figure caption text.
        chart_title: In-image chart title.
        slug: Filename prefix for the rendered PNG (mast/pair names).
        x_labels: Ordered x-panel labels (facet columns).
        y_labels: Ordered y-panel labels (facet rows, or columns when the
            grid has a single x label, e.g. 2.3.7's ERA5 source).
        pairs_df: Tidy scatter points [x_label, y_label, x, y] — raw
            timeseries data lives in meta, never in the schema (same
            convention as the representative-year figure atom).
    """

    caption: str = ""
    chart_title: str = ""
    slug: str = ""
    x_labels: list[str] = field(default_factory=list)
    y_labels: list[str] = field(default_factory=list)
    pairs_df: pl.DataFrame = field(default_factory=pl.DataFrame)


@dataclass(frozen=True)
class TowerShadingMethodAtomMeta:
    """Metadata for the 2.3.4 method-text atom.

    Attributes:
        mast_names: Masts covered by the subsection (input order).
    """

    mast_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TowerShadingSectorTableAtomMeta:
    """Metadata for one per-height sector comparison table atom (2.3.4).

    Attributes:
        mast_name: Mast the corrected height belongs to.
        height: Corrected (merged) height in meters.
        channel_1_label / channel_2_label: Display labels of the two source
            channels — sensor directions (e.g. ESE/WNW) when discoverable
            from the clean-stage sensor metadata, else 通道1/通道2.
    """

    mast_name: str
    height: float
    channel_1_label: str = "通道1"
    channel_2_label: str = "通道2"
