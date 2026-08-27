"""Report schemas for the cleaning capability."""

import dataframely as dy


class CleaningPlaceholderSchema(dy.Schema):
    """Schema for Wave 1 placeholder atoms.

    One row holding the placeholder line rendered as the subsection body.
    Wave 2 replaces this with the real per-subsection schemas.
    """

    text = dy.String(nullable=False)


class CleaningCoverageSchema(dy.Schema):
    """Long format for the 2.3.2 stage-coverage table.

    One row per mast × cleaning height (``cleaning_heights`` — the only
    heights source). ``raw_points`` / ``clean_points`` are NULL when the
    stage input is missing (rendered as an em-dash); ``clean_points``
    counts tower-shading output when available, else process-clean output;
    ``final_points`` counts the reconstruct-meso series clipped to the
    analysis window.
    """

    mast_name = dy.String(nullable=False)
    height = dy.Float64(nullable=False)
    expected_points = dy.Int64(nullable=False, min=0)
    raw_points = dy.Int64(nullable=True, min=0)
    clean_points = dy.Int64(nullable=True, min=0)
    final_points = dy.Int64(nullable=False, min=0)


class CleaningRulesSchema(dy.Schema):
    """One row per enabled cleaning rule (rules table of 2.3.3).

    rule_name/sensor_type keep the process-clean.toml source values;
    translation to Chinese happens at render time. height_min/max are
    None when the height-filter bound is unbounded. ``condition`` is the
    pre-formatted human-readable judgement criterion.
    """

    rule_name = dy.String(nullable=False)
    sensor_type = dy.String(nullable=False)
    height_min = dy.Float64(nullable=True)
    height_max = dy.Float64(nullable=True)
    condition = dy.String(nullable=False)


class CleaningViolationsSchema(dy.Schema):
    """One row per (mast, column, rule) violation count (2.3.3 table).

    rule_name keeps the process-clean.toml source value; translation
    happens at render time. The mast-level violation_percentage lives in
    the section summary, not in per-rule rows.
    """

    mast_name = dy.String(nullable=False)
    column_name = dy.String(nullable=False)
    rule_name = dy.String(nullable=False)
    violation_count = dy.Int64(nullable=False, min=0)


class CorrelationLongSchema(dy.Schema):
    """Long-format correlation matrix rows (2.3.5 table).

    One row per (x_label, y_label) pair of the full square incl. the
    diagonal. ``r`` is NULL when the pair has no computable correlation
    (fewer than two complete rows or zero variance).
    """

    x_label = dy.String(nullable=False)
    y_label = dy.String(nullable=False)
    r = dy.Float64(nullable=True)


class ScatterPanelSchema(dy.Schema):
    """Per-panel OLS statistics for the scatter-regression figure atoms.

    One row per rendered scatter panel; (x_label, y_label) is unique.
    Values are NULL only if a future caller deposits an unregressable
    panel — builders skip those panels entirely.
    """

    x_label = dy.String(nullable=False)
    y_label = dy.String(nullable=False)
    slope = dy.Float64(nullable=True)
    intercept = dy.Float64(nullable=True)
    r = dy.Float64(nullable=True)
    rmse = dy.Float64(nullable=True)
    n_pairs = dy.Int64(nullable=True, min=0)


class TowerShadingMethodSchema(dy.Schema):
    """One-row schema for the 2.3.4 method-text atom.

    Holds the constant method sentence; the max-merge formula renders as a
    TypstEquation in the section body (air-density convention).
    """

    text = dy.String(nullable=False)


class TowerShadingSectorSchema(dy.Schema):
    """Per-sector before/after comparison rows for one corrected height (2.3.4).

    One row per 16-sector bin with observed data, plus one weighted
    ``总体平均(加权)`` row (``is_overall=True``). ``delta_*`` are signed
    after − before (m/s); ``pct_*`` are signed relative changes (NULL when
    the before-mean is 0, rendered as N/A).
    """

    sector = dy.String(nullable=False)
    data_points = dy.Int64(nullable=False, min=0)
    mean_before_1 = dy.Float64(nullable=False)
    mean_before_2 = dy.Float64(nullable=False)
    mean_after = dy.Float64(nullable=False)
    delta_1 = dy.Float64(nullable=False)
    delta_2 = dy.Float64(nullable=False)
    pct_1 = dy.Float64(nullable=True)
    pct_2 = dy.Float64(nullable=True)
    is_overall = dy.Bool(nullable=False)