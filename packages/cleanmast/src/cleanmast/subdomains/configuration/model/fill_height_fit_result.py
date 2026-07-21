"""FillHeightFitResult — trained fill-height model parameters.

One instance per mast x strategy x variable, persisted under
``fill-models/{mast}/{strategy}/{variable}-fit.toml`` in the project
directory, e.g.::

    fill-models/M5057/remove-top-layer/ws-fit.toml

The field names are strategy-agnostic on purpose: ``removed_height``,
``reference_heights``, ``shear`` and ``deg_diff_per_m`` cover the
``remove-top-layer`` strategy.  Future strategies (e.g.
``per-timestamp-extrapolation``) extend with additional optional fields or
introduce strategy-specific sibling models in this package.
"""

from typing import Literal

from pydantic import BaseModel


class FillHeightFitResult(BaseModel):
    """Trained fill-height model: one per mast x strategy x variable.

    Stored at: fill-models/{mast}/{strategy}/{variable}-fit.toml
    e.g.:      fill-models/M5057/remove-top-layer/ws-fit.toml

    Attributes:
        strategy: Fill strategy identifier (e.g. "remove-top-layer").
        target_type: Variable the model predicts.
        removed_height: Height of the removed ground-truth layer.
        reference_heights: Heights of sensors used for fitting.
        shear: WS-only: power law shear exponent.
        deg_diff_per_m: WD-only: direction change per metre.
        r_squared: Goodness of fit, when available.
        n_points: Number of points used in the fit, when available.
    """

    strategy: str
    target_type: Literal["WindSpeed", "WindDirection"]
    removed_height: float
    reference_heights: list[float]
    shear: float | None = None
    deg_diff_per_m: float | None = None
    r_squared: float | None = None
    n_points: int | None = None
