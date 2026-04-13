"""Fifty-year max wind summary calculator.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating fifty-year max wind summary
comparisons across Method 1/2/3 and IEC wind class classification.
"""

from typing import cast

import polars as pl

from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    FiftyYearMaxWindComparisonSchema,
    FiftyYearMaxWindMethod1DetailSchema,
    FiftyYearMaxWindResultSchema,
    IECWindClassSchema,
)


class SummaryCalculator:
    """Calculate fifty-year max wind summary comparing all methods.

    Produces:
    - Sustained wind comparison across Method 1/2/3
    - Extreme wind comparison across Method 1/2/3
    - IEC wind class reference table
    """

    def calculate(
        self,
        method1_result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
        method2_sustained: AnalysisResult[FiftyYearMaxWindResultSchema],
        method2_extreme: AnalysisResult[FiftyYearMaxWindResultSchema],
        method3_sustained: AnalysisResult[FiftyYearMaxWindResultSchema],
        method3_extreme: AnalysisResult[FiftyYearMaxWindResultSchema],
    ) -> tuple[
        AnalysisResult[FiftyYearMaxWindComparisonSchema],
        AnalysisResult[FiftyYearMaxWindComparisonSchema],
        AnalysisResult[IECWindClassSchema],
    ]:
        """Calculate comparison tables and IEC wind class table.

        Args:
            method1_result: Method 1 detail result (contains both sustained and extreme)
            method2_sustained: Method 2 sustained result
            method2_extreme: Method 2 extreme result
            method3_sustained: Method 3 sustained result
            method3_extreme: Method 3 extreme result

        Returns:
            Tuple of (sustained_comparison, extreme_comparison, iec_wind_class)
        """
        sustained_comp = self._build_comparison(
            method1_result=method1_result,
            method2_result=method2_sustained,
            method3_result=method3_sustained,
            wind_speed_type="sustained",
        )
        extreme_comp = self._build_comparison(
            method1_result=method1_result,
            method2_result=method2_extreme,
            method3_result=method3_extreme,
            wind_speed_type="extreme",
        )
        iec_result = self._build_iec_result(sustained_comp, extreme_comp, method1_result)

        return sustained_comp, extreme_comp, iec_result

    def _build_comparison(
        self,
        method1_result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
        method2_result: AnalysisResult[FiftyYearMaxWindResultSchema],
        method3_result: AnalysisResult[FiftyYearMaxWindResultSchema],
        wind_speed_type: str,
    ) -> AnalysisResult[FiftyYearMaxWindComparisonSchema]:
        """Build comparison DataFrame for a given wind speed type.

        Args:
            method1_result: Method 1 detail result
            method2_result: Method 2 result for the wind speed type
            method3_result: Method 3 result for the wind speed type
            wind_speed_type: "sustained" or "extreme"

        Returns:
            AnalysisResult with FiftyYearMaxWindComparisonSchema
        """
        # Extract standard_density_wind_speed per height from each method
        method1_map = self._extract_method1_values(method1_result, wind_speed_type)
        method2_map = self._extract_method_values(method2_result, wind_speed_type)
        method3_map = self._extract_method_values(method3_result, wind_speed_type)

        all_heights = set(method1_map.keys()) | set(method2_map.keys()) | set(method3_map.keys())

        rows: list[dict] = []
        for height in sorted(all_heights):
            method1_value, method1_marker = method1_map.get(height, (0.0, ""))
            method2_value, method2_marker = method2_map.get(height, (0.0, ""))
            method3_value, method3_marker = method3_map.get(height, (0.0, ""))

            # Pick any non-empty interpolation marker
            marker = method1_marker or method2_marker or method3_marker
            conservative_max = max(method1_value, method2_value, method3_value)

            rows.append({
                "height": height,
                "method1": method1_value,
                "method2": method2_value,
                "method3": method3_value,
                "conservative_max": conservative_max,
                "wind_speed_type": wind_speed_type,
                "interpolation_marker": marker,
            })

        result_df = pl.DataFrame(rows) if rows else self._create_empty_comparison_dataframe(wind_speed_type)

        return AnalysisResult.create(
            schema=FiftyYearMaxWindComparisonSchema,
            data=result_df,
            metadata=method1_result.metadata,
        )

    def _extract_method1_values(
        self,
        result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
        wind_speed_type: str,
    ) -> dict[float, tuple[float, str]]:
        """Extract standard_density_wind_speed and interpolation_marker from Method 1 result.

        Args:
            result: Method 1 analysis result
            wind_speed_type: "sustained" or "extreme"

        Returns:
            Dict mapping height to (standard_density_wind_speed, interpolation_marker)
        """
        df = result.data.filter(pl.col("wind_speed_type") == wind_speed_type)
        values: dict[float, tuple[float, str]] = {}
        for row in df.iter_rows(named=True):
            marker = row.get("interpolation_marker") or ""
            values[cast(float, row["height"])] = (
                cast(float, row["standard_density_wind_speed"]),
                str(marker) if marker is not None else "",
            )
        return values

    def _extract_method_values(
        self,
        result: AnalysisResult[FiftyYearMaxWindResultSchema],
        wind_speed_type: str,
    ) -> dict[float, tuple[float, str]]:
        """Extract standard_density_wind_speed and interpolation_marker from Method 2/3 result.

        Args:
            result: Method 2 or 3 analysis result
            wind_speed_type: "sustained" or "extreme"

        Returns:
            Dict mapping height to (standard_density_wind_speed, interpolation_marker)
        """
        df = result.data.filter(pl.col("wind_speed_type") == wind_speed_type)
        values: dict[float, tuple[float, str]] = {}
        for row in df.iter_rows(named=True):
            marker = row.get("interpolation_marker") or ""
            values[cast(float, row["height"])] = (
                cast(float, row["standard_density_wind_speed"]),
                str(marker) if marker is not None else "",
            )
        return values

    def _build_iec_result(
        self,
        sustained_comp: AnalysisResult[FiftyYearMaxWindComparisonSchema],
        extreme_comp: AnalysisResult[FiftyYearMaxWindComparisonSchema],
        method1_result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
    ) -> AnalysisResult[IECWindClassSchema]:
        """Build IEC wind class reference table with per-height classification.

        Args:
            sustained_comp: Sustained wind comparison result
            extreme_comp: Extreme wind comparison result
            method1_result: Any input result to borrow metadata from

        Returns:
            AnalysisResult with IECWindClassSchema
        """
        # Reference rows
        rows: list[dict] = [
            {"wind_class": "I", "height": None, "sustained_threshold": 50.0, "extreme_threshold": 70.0, "conservative_sustained": None, "conservative_extreme": None},
            {"wind_class": "II", "height": None, "sustained_threshold": 42.5, "extreme_threshold": 59.5, "conservative_sustained": None, "conservative_extreme": None},
            {"wind_class": "III", "height": None, "sustained_threshold": 37.5, "extreme_threshold": 52.5, "conservative_sustained": None, "conservative_extreme": None},
            {"wind_class": "S", "height": None, "sustained_threshold": 0.0, "extreme_threshold": 0.0, "conservative_sustained": None, "conservative_extreme": None},
        ]

        # Build per-height lookup for conservative values
        extreme_lookup: dict[float, float] = {}
        for row in extreme_comp.data.iter_rows(named=True):
            extreme_lookup[cast(float, row["height"])] = cast(float, row["conservative_max"])

        for row in sustained_comp.data.sort("height").iter_rows(named=True):
            height = cast(float, row["height"])
            sustained = cast(float, row["conservative_max"])
            extreme = extreme_lookup.get(height, 0.0)

            wind_class = self._classify_wind_class(sustained, extreme)

            rows.append({
                "wind_class": wind_class,
                "height": height,
                "sustained_threshold": 0.0,
                "extreme_threshold": 0.0,
                "conservative_sustained": sustained,
                "conservative_extreme": extreme,
            })

        df = pl.DataFrame(rows)

        return AnalysisResult.create(
            schema=IECWindClassSchema,
            data=df,
            metadata=method1_result.metadata,
        )

    def _classify_wind_class(self, sustained: float, extreme: float) -> str:
        """Classify IEC wind class based on conservative sustained and extreme wind speeds.

        Args:
            sustained: Conservative sustained wind speed
            extreme: Conservative extreme wind speed

        Returns:
            IEC wind class: I, II, III, or S
        """
        if sustained <= 37.5 and extreme <= 52.5:
            return "III"
        elif sustained <= 42.5 and extreme <= 59.5:
            return "II"
        elif sustained <= 50.0 and extreme <= 70.0:
            return "I"
        else:
            return "S"

    def _create_empty_comparison_dataframe(self, wind_speed_type: str) -> pl.DataFrame:
        """Create an empty comparison DataFrame with correct schema.

        Args:
            wind_speed_type: "sustained" or "extreme"

        Returns:
            Empty polars DataFrame
        """
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "method1": pl.Series([], dtype=pl.Float64),
            "method2": pl.Series([], dtype=pl.Float64),
            "method3": pl.Series([], dtype=pl.Float64),
            "conservative_max": pl.Series([], dtype=pl.Float64),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "interpolation_marker": pl.Series([], dtype=pl.String),
        })
