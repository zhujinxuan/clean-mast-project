"""Base protocol and types for fill-heights strategies.

This module defines the HeightStrategy Protocol that all height-filling strategies
must implement. The design uses Python's Protocol (structural subtyping) rather than
ABC (abstract base classes) for several important reasons.

Design Philosophy:
==================

1. WHY PROTOCOL INSTEAD OF ABC:
   - Protocol uses structural subtyping: a class satisfies the protocol if it has
     the required methods, not if it inherits from a base class
   - No inheritance hierarchy needed - strategies can come from any class
   - More flexible for composition and testing
   - Better IDE support (methods are checked structurally)
   - Avoids diamond inheritance issues

2. WHY TypeVar T:
   - HeightStrategy is generic in the return type (T)
   - T is constrained to WindSpeedHeightConfig or WindDirectionHeightConfig
   - This enables type-safe dispatch: WSHeightStrategy vs WDHeightStrategy
   - The 'covariant=True' allows subclasses to return more specific types

3. WHY PRE-FITTED PARAMETERS:
   - Strategies receive pre-calculated parameters (shear, deg_diff_per_m)
   - This separates concerns: fitting (done once) vs configuration (per target)
   - Enables dual-config generation with same parameters
   - Prevents redundant computation for each target height

Protocol Hierarchy:
==================

    HeightStrategy[T] (Protocol)
        ├── WSHeightStrategy = HeightStrategy[WindSpeedHeightConfig]
        │   ├── WSExtrapolateTop3Strategy
        │   └── WSInterpolateInterStrategy
        │
        └── WDHeightStrategy = HeightStrategy[WindDirectionHeightConfig]
            ├── WDExtrapolateTop3Strategy
            └── WDInterpolateInterStrategy

Each strategy implements:
    - name: Class attribute for identification
    - build_config(): Method to generate configuration for a target height

Example Strategy Implementation:
==================================

    class WSExtrapolateTop3Strategy:
        name = "ws-extrapolate-top3"

        def build_config(
            self,
            timeseries: TimeSeriesData,
            target_height: float,
            shear: float,  # Pre-fitted!
        ) -> WindSpeedHeightConfig | None:
            # Build config if applicable, None otherwise
            ...
"""
