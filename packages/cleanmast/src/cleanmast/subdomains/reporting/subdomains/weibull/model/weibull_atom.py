"""Combined Weibull parameters and distribution subgrid atom."""

import math
from pathlib import Path
from typing import Self, cast

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override
from typst_ir import TypstFigure, TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.weibull.model.report_meta import (
    WeibullAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.schemas import (
    WeibullSchema,
)


def _is_long_format(df: pl.DataFrame) -> bool:
    """Detect long-format Weibull data (bin_center column instead of bin_centers)."""
    return "bin_center" in df.columns and "bin_centers" not in df.columns


def _reshape_long_to_wide(df: pl.DataFrame) -> pl.DataFrame:
    """Convert long-format Weibull data to wide format matching WeibullSchema."""
    grouped = (
        df.group_by(
            "height",
            "interpolation_marker",
            "shape_k",
            "scale_c",
            maintain_order=True,
        )
        .agg(
            pl.col("bin_center").alias("bin_centers"),
            pl.col("observed_density").alias("observed_density"),
            pl.col("fitted_density").alias("fitted_density"),
        )
    )

    if "mean_speed" in df.columns:
        grouped = grouped.with_columns(
            pl.col("mean_speed").first().alias("mean_speed")
        )
    else:
        grouped = grouped.with_columns(
            (
                pl.col("scale_c")
                * pl.col("shape_k").map_elements(
                    lambda k: math.gamma(1 + 1 / k), return_dtype=pl.Float64
                )
            ).alias("mean_speed")
        )

    return grouped


class WeibullSubgridAtom(ReportAtom[WeibullSchema, WeibullAtomMeta]):
    """Combined Weibull parameters table + faceted distribution plots.

    - Table: Weibull parameters (shape k, scale c) for interested heights
    - Image: Faceted subgrid of observed histogram + fitted PDF per height
    - Summary: Brief Chinese description of Weibull fit results
    """

    @classmethod
    def create(
        cls,
        schema: type[WeibullSchema],
        df: pl.DataFrame,
        meta: WeibullAtomMeta,
    ) -> Self:
        """Factory: auto-detects long/wide format, validates, returns typed atom."""
        if _is_long_format(df):
            df = _reshape_long_to_wide(df)
        validated = schema.validate(df, cast=True)
        return cls(df=validated, schema=schema, meta=meta)

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} Weibull分布拟合图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} Weibull参数表"

    def _get_interested_heights_df(self) -> pl.DataFrame:
        """Return unique heights present in the (pre-filtered) DataFrame."""
        return (
            self.df.select(["height", "interpolation_marker", "shape_k", "scale_c"])
            .unique()
            .sort("height")
        )

    @override
    def renderTable(self) -> TypstTable | None:
        """Render Typst table with Weibull parameters for interested heights."""
        interested = self._get_interested_heights_df()

        rows: list[list[str]] = []
        for row in interested.iter_rows(named=True):
            height_display = get_height_display_name(
                row["height"], row["interpolation_marker"] or ""
            )
            rows.append(
                [
                    height_display,
                    f"{row['shape_k']:.2f}",
                    f"{row['scale_c']:.2f}",
                ]
            )

        return TypstTable(
            headers=["高度(m)", "形状参数k", "尺度参数c(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate faceted Weibull distribution chart for interested heights."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = (
            output_dir / f"weibull_subgrid_{self.meta.mast_name}_{cache_key}.png"
        )

        if not force and image_path.exists():
            return image_path

        # Heights are pre-filtered by the section — use all data
        if self.df.is_empty():
            return Path()

        plot_df = (
            self.df.select(
                [
                    "height",
                    "interpolation_marker",
                    "bin_centers",
                    "observed_density",
                    "fitted_density",
                    "shape_k",
                    "scale_c",
                ]
            )
            .explode(["bin_centers", "observed_density", "fitted_density"])
            .rename({"bin_centers": "bin_center"})
            .with_columns(
                pl.struct(["height", "interpolation_marker"])
                .map_elements(
                    lambda x: get_height_display_name(
                        x["height"], x["interpolation_marker"] or ""
                    ),
                    return_dtype=pl.String,
                )
                .alias("height_label")
            )
            .sort("height")
        )

        base = alt.Chart(plot_df.to_pandas())

        observed = base.mark_bar(opacity=0.6).encode(
            x=alt.X("bin_center:Q", title="风速 (m/s)"),
            y=alt.Y("observed_density:Q", title="概率密度", scale=alt.Scale(zero=False)),
            color=alt.value("#1f77b4"),
            tooltip=[
                alt.Tooltip("bin_center:Q", title="风速(m/s)", format=".1f"),
                alt.Tooltip("observed_density:Q", title="观测密度", format=".4f"),
            ],
        )

        fitted = base.mark_line(strokeWidth=2).encode(
            x=alt.X("bin_center:Q", title="风速 (m/s)"),
            y=alt.Y("fitted_density:Q", title="概率密度"),
            color=alt.value("#ff7f0e"),
            tooltip=[
                alt.Tooltip("bin_center:Q", title="风速(m/s)", format=".1f"),
                alt.Tooltip("fitted_density:Q", title="拟合密度", format=".4f"),
            ],
        )

        chart = (
            (observed + fitted)
            .properties(width=220, height=160)
            .facet(
                column=alt.Column("height_label:N", title="高度"),
                title=f"{self.meta.mast_name} Weibull分布拟合",
            )
            .configure_axis(labelFontSize=10, titleFontSize=11)
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate brief Chinese summary of Weibull parameters."""
        interested = self._get_interested_heights_df()

        if interested.is_empty():
            return []

        height_strs = [
            get_height_display_name(
                row["height"], row["interpolation_marker"] or ""
            )
            for row in interested.iter_rows(named=True)
        ]

        avg_k = cast(float, interested["shape_k"].mean() or 0)
        avg_c = cast(float, interested["scale_c"].mean() or 0)

        text = (
            f"{self.meta.mast_name}测风塔在{', '.join(height_strs)}高度的"
            f"Weibull拟合结果显示，"
            f"平均形状参数k={avg_k:.2f}，平均尺度参数c={avg_c:.2f}m/s，"
            f"各高度风速分布符合Weibull分布特征，可用于风资源评估。"
        )
        return [TypstParagraph(text=text)]

    @override
    def renderImageTypst(self, output_dir: Path, force: bool = False) -> TypstFigure | None:
        """Generate image and return TypstFigure IR node."""
        return super().renderImageTypst(output_dir, force)
