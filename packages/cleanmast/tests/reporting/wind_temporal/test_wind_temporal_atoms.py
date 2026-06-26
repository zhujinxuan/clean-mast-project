"""Tests for wind temporal pattern atoms in the reporting domain.

Tests cover all 6 temporal pattern atoms:
- SingleMastDailyPatternAtom
- SingleMastDailyPowerPatternAtom
- SingleMastMonthlyPatternAtom
- SingleMastMonthlyPowerPatternAtom
- SingleMastMonthlyDailyWindAtom
- SingleMastMonthlyDailyPowerAtom
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.daily_pattern_atom import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.daily_power_pattern_atom import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_daily_power_atom import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_daily_wind_atom import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_pattern_atom import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_power_pattern_atom import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.report_meta import (
    WindTemporalAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.schemas import (
    TemporalPatternSchema,
)
from typst_ir import TypstParagraph, TypstTable


@pytest.fixture
def sample_mast_meta() -> WindTemporalAtomMeta:
    """Create sample WindTemporalAtomMeta for testing."""
    return WindTemporalAtomMeta(mast_name="M01")


@pytest.fixture
def sample_daily_pattern_df() -> pl.DataFrame:
    """Create sample daily pattern DataFrame."""
    rows = []
    base_time = datetime(2023, 1, 1)

    for height in [100.0, 120.0]:
        for hour in range(24):
            speed = 5.0 + 3.0 * (1 if 6 <= hour <= 18 else 0)
            power = 0.5 * 1.225 * (speed ** 3)
            marker = "外推" if height > 100 else None

            rows.append({
                "timestamp": base_time + timedelta(hours=hour),
                "hour": hour,
                "month": 1,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_monthly_pattern_df() -> pl.DataFrame:
    """Create sample monthly pattern DataFrame."""
    rows = []
    base_time = datetime(2023, 1, 15)

    for height in [100.0, 120.0]:
        marker = "外推" if height > 100 else None
        for month in range(1, 13):
            if month in [12, 1, 2]:
                speed = 10.0
            elif month in [6, 7, 8]:
                speed = 5.0
            else:
                speed = 7.5

            power = 0.5 * 1.225 * (speed ** 3)

            rows.append({
                "timestamp": base_time.replace(month=month),
                "hour": 0,
                "month": month,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_monthly_daily_df() -> pl.DataFrame:
    """Create sample monthly-daily pattern DataFrame."""
    rows = []

    for month in [1, 4, 7, 10]:
        base_time = datetime(2023, month, 15)
        for hour in range(24):
            for height in [100.0, 120.0]:
                marker = "外推" if height > 100 else None
                month_factor = 1.5 if month in [12, 1] else 1.0
                hour_factor = 1.2 if 6 <= hour <= 18 else 0.8

                speed = 5.0 * month_factor * hour_factor
                power = 0.5 * 1.225 * (speed ** 3)

                rows.append({
                    "timestamp": base_time + timedelta(hours=hour),
                    "hour": hour,
                    "month": month,
                    "wind_speed": speed,
                    "wind_power": power,
                    "height": height,
                    "mean_speed": speed,
                    "mean_power": power,
                    "interpolation_marker": marker,
                })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_monthly_daily_df_full() -> pl.DataFrame:
    """Create full monthly-daily pattern DataFrame with all 12 months."""
    rows = []

    for month in range(1, 13):
        base_time = datetime(2023, month, 15)
        for hour in range(24):
            for height in [100.0, 120.0]:
                marker = "外推" if height > 100 else None
                speed = 5.0 + (month % 3) + (hour % 12) * 0.1
                power = 0.5 * 1.225 * (speed ** 3)

                rows.append({
                    "timestamp": base_time + timedelta(hours=hour),
                    "hour": hour,
                    "month": month,
                    "wind_speed": speed,
                    "wind_power": power,
                    "height": height,
                    "mean_speed": speed,
                    "mean_power": power,
                    "interpolation_marker": marker,
                })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_monthly_pattern_agree_df() -> pl.DataFrame:
    """Create monthly pattern DataFrame where both heights agree on peak/min months."""
    rows = []
    base_time = datetime(2023, 1, 15)

    for height in [100.0, 120.0]:
        marker = "外推" if height > 100 else None
        for month in range(1, 13):
            if month == 4:
                speed = 10.0
            elif month == 7:
                speed = 4.0
            else:
                speed = 7.0

            power = 0.5 * 1.225 * (speed ** 3)

            rows.append({
                "timestamp": base_time.replace(month=month),
                "hour": 0,
                "month": month,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_monthly_pattern_disagree_df() -> pl.DataFrame:
    """Create monthly pattern DataFrame where heights disagree on peak/min months."""
    rows = []
    base_time = datetime(2023, 1, 15)

    for height in [100.0, 120.0]:
        marker = "外推" if height > 100 else None
        for month in range(1, 13):
            if height == 100.0:
                if month == 4:
                    speed = 10.0
                elif month == 7:
                    speed = 4.0
                else:
                    speed = 7.0
            else:
                if month == 5:
                    speed = 10.0
                elif month == 8:
                    speed = 4.0
                else:
                    speed = 7.0

            power = 0.5 * 1.225 * (speed ** 3)

            rows.append({
                "timestamp": base_time.replace(month=month),
                "hour": 0,
                "month": month,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_daily_pattern_agree_df() -> pl.DataFrame:
    """Create daily pattern DataFrame where both heights agree on peak/min hours."""
    rows = []
    base_time = datetime(2023, 1, 1)

    for height in [100.0, 120.0]:
        for hour in range(24):
            if hour == 14:
                speed = 10.0
            elif hour == 8:
                speed = 4.0
            else:
                speed = 7.0

            power = 0.5 * 1.225 * (speed ** 3)
            marker = "外推" if height > 100 else None

            rows.append({
                "timestamp": base_time + timedelta(hours=hour),
                "hour": hour,
                "month": 1,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_daily_pattern_disagree_df() -> pl.DataFrame:
    """Create daily pattern DataFrame where heights disagree on peak/min hours."""
    rows = []
    base_time = datetime(2023, 1, 1)

    for height in [100.0, 120.0]:
        for hour in range(24):
            if height == 100.0:
                if hour == 14:
                    speed = 10.0
                elif hour == 8:
                    speed = 4.0
                else:
                    speed = 7.0
            else:
                if hour == 16:
                    speed = 10.0
                elif hour == 6:
                    speed = 4.0
                else:
                    speed = 7.0

            power = 0.5 * 1.225 * (speed ** 3)
            marker = "外推" if height > 100 else None

            rows.append({
                "timestamp": base_time + timedelta(hours=hour),
                "hour": hour,
                "month": 1,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": speed,
                "mean_power": power,
                "interpolation_marker": marker,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def daily_pattern_atom(
    sample_daily_pattern_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
    ) -> SingleMastDailyPatternAtom:
    """Create a SingleMastDailyPatternAtom for testing."""
    return SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_power_pattern_atom(
    sample_daily_pattern_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastDailyPowerPatternAtom:
    """Create a SingleMastDailyPowerPatternAtom for testing."""
    return SingleMastDailyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_pattern_atom(
    sample_monthly_pattern_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPatternAtom:
    """Create a SingleMastMonthlyPatternAtom for testing."""
    return SingleMastMonthlyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_power_pattern_atom(
    sample_monthly_pattern_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPowerPatternAtom:
    """Create a SingleMastMonthlyPowerPatternAtom for testing."""
    return SingleMastMonthlyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_daily_wind_atom(
    sample_monthly_daily_df_full: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyDailyWindAtom:
    """Create a SingleMastMonthlyDailyWindAtom for testing."""
    return SingleMastMonthlyDailyWindAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_daily_df_full,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_daily_power_atom(
    sample_monthly_daily_df_full: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyDailyPowerAtom:
    """Create a SingleMastMonthlyDailyPowerAtom for testing."""
    return SingleMastMonthlyDailyPowerAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_daily_df_full,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_pattern_agree_atom(
    sample_monthly_pattern_agree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPatternAtom:
    """Create a SingleMastMonthlyPatternAtom with agreeing heights."""
    return SingleMastMonthlyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_agree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_power_pattern_agree_atom(
    sample_monthly_pattern_agree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPowerPatternAtom:
    """Create a SingleMastMonthlyPowerPatternAtom with agreeing heights."""
    return SingleMastMonthlyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_agree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_pattern_disagree_atom(
    sample_monthly_pattern_disagree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPatternAtom:
    """Create a SingleMastMonthlyPatternAtom with disagreeing heights."""
    return SingleMastMonthlyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_disagree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_power_pattern_disagree_atom(
    sample_monthly_pattern_disagree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastMonthlyPowerPatternAtom:
    """Create a SingleMastMonthlyPowerPatternAtom with disagreeing heights."""
    return SingleMastMonthlyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_pattern_disagree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_pattern_agree_atom(
    sample_daily_pattern_agree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastDailyPatternAtom:
    """Create a SingleMastDailyPatternAtom with agreeing heights."""
    return SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_agree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_power_pattern_agree_atom(
    sample_daily_pattern_agree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastDailyPowerPatternAtom:
    """Create a SingleMastDailyPowerPatternAtom with agreeing heights."""
    return SingleMastDailyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_agree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_pattern_disagree_atom(
    sample_daily_pattern_disagree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastDailyPatternAtom:
    """Create a SingleMastDailyPatternAtom with disagreeing heights."""
    return SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_disagree_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_power_pattern_disagree_atom(
    sample_daily_pattern_disagree_df: pl.DataFrame,
    sample_mast_meta: WindTemporalAtomMeta,
) -> SingleMastDailyPowerPatternAtom:
    """Create a SingleMastDailyPowerPatternAtom with disagreeing heights."""
    return SingleMastDailyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_daily_pattern_disagree_df,
        meta=sample_mast_meta,
    )


class TestSingleMastDailyPatternAtom:
    """Tests for SingleMastDailyPatternAtom."""

    def test_render_image(self, daily_pattern_atom: SingleMastDailyPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = daily_pattern_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, daily_pattern_atom: SingleMastDailyPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with 24 hours."""
        table = daily_pattern_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert len(table.headers) > 0
        assert "小时" in table.headers
        assert len(table.data) == 24

    def test_render_summary(self, daily_pattern_atom: SingleMastDailyPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = daily_pattern_atom.renderSummary()

        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert len(summary[0].text) > 0
        assert "测风塔" in summary[0].text
        assert "日平均风速" in summary[0].text

    def test_content_hash_consistency(self, daily_pattern_atom: SingleMastDailyPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = daily_pattern_atom.get_or_compute_df_hashkey()
        hash2 = daily_pattern_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastDailyPatternAtom_" in hash1


class TestSingleMastDailyPowerPatternAtom:
    """Tests for SingleMastDailyPowerPatternAtom."""

    def test_render_image(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = daily_power_pattern_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with power data."""
        table = daily_power_pattern_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert len(table.headers) > 0
        assert "小时" in table.headers

    def test_render_summary(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = daily_power_pattern_atom.renderSummary()

        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert len(summary[0].text) > 0
        assert "测风塔" in summary[0].text
        assert "日平均风功率密度" in summary[0].text

    def test_content_hash_consistency(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = daily_power_pattern_atom.get_or_compute_df_hashkey()
        hash2 = daily_power_pattern_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastDailyPowerPatternAtom_" in hash1


class TestSingleMastMonthlyPatternAtom:
    """Tests for SingleMastMonthlyPatternAtom."""

    def test_render_image(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_pattern_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with 13 rows including average."""
        table = monthly_pattern_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert len(table.headers) > 0
        assert "月份" in table.headers
        assert len(table.data) == 13
        assert table.data[0][0] == "平均"

    def test_render_summary(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_pattern_atom.renderSummary()

        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert len(summary[0].text) > 0
        assert "测风塔" in summary[0].text
        assert "月平均风速" in summary[0].text

    def test_content_hash_consistency(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_pattern_atom.get_or_compute_df_hashkey()
        hash2 = monthly_pattern_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastMonthlyPatternAtom_" in hash1


class TestSingleMastMonthlyPowerPatternAtom:
    """Tests for SingleMastMonthlyPowerPatternAtom."""

    def test_render_image(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_power_pattern_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with 13 rows including average."""
        table = monthly_power_pattern_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert len(table.headers) > 0
        assert "月份" in table.headers
        assert len(table.data) == 13
        assert table.data[0][0] == "平均"

    def test_render_summary(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_power_pattern_atom.renderSummary()

        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert len(summary[0].text) > 0
        assert "测风塔" in summary[0].text
        assert "月平均风功率密度" in summary[0].text

    def test_content_hash_consistency(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_power_pattern_atom.get_or_compute_df_hashkey()
        hash2 = monthly_power_pattern_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastMonthlyPowerPatternAtom_" in hash1


class TestSingleMastMonthlyDailyWindAtom:
    """Tests for SingleMastMonthlyDailyWindAtom."""

    def test_render_image(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_daily_wind_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table_returns_none(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test renderTable returns None for monthly-daily wind atom."""
        table = monthly_daily_wind_atom.renderTable()

        assert table is None

    def test_render_summary_returns_empty(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test renderSummary returns empty list for monthly-daily wind atom."""
        summary = monthly_daily_wind_atom.renderSummary()

        assert summary == []

    def test_content_hash_consistency(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_daily_wind_atom.get_or_compute_df_hashkey()
        hash2 = monthly_daily_wind_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastMonthlyDailyWindAtom_" in hash1


class TestSingleMastMonthlyDailyPowerAtom:
    """Tests for SingleMastMonthlyDailyPowerAtom."""

    def test_render_image(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_daily_power_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table_returns_none(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test renderTable returns None for monthly-daily power atom."""
        table = monthly_daily_power_atom.renderTable()

        assert table is None

    def test_render_summary_returns_empty(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test renderSummary returns empty list for monthly-daily power atom."""
        summary = monthly_daily_power_atom.renderSummary()

        assert summary == []

    def test_content_hash_consistency(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_daily_power_atom.get_or_compute_df_hashkey()
        hash2 = monthly_daily_power_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "SingleMastMonthlyDailyPowerAtom_" in hash1


class TestMonthlyPatternAgreement:
    """Tests for monthly pattern agreement behavior."""

    def test_agree_renders_exact_summary_text(
        self,
        monthly_pattern_agree_atom: SingleMastMonthlyPatternAtom,
    ) -> None:
        """When all heights agree, summary contains exact expected text."""
        summary = monthly_pattern_agree_atom.renderSummary()

        assert len(summary) == 1
        assert isinstance(summary[0], TypstParagraph)
        expected = "M01测风塔 100m、120m 高度月平均风速 7.00m/s、7.00m/s，最大值都出现在 4 月，最小值都出现在 7 月。"
        assert summary[0].text == expected

    def test_disagree_renders_empty_summary(
        self,
        monthly_pattern_disagree_atom: SingleMastMonthlyPatternAtom,
    ) -> None:
        """When heights disagree, summary is empty."""
        summary = monthly_pattern_disagree_atom.renderSummary()

        assert summary == []


class TestMonthlyPowerPatternAgreement:
    """Tests for monthly power pattern agreement behavior."""

    def test_agree_renders_exact_summary_text(
        self,
        monthly_power_pattern_agree_atom: SingleMastMonthlyPowerPatternAtom,
    ) -> None:
        """When all heights agree, summary contains exact expected text."""
        summary = monthly_power_pattern_agree_atom.renderSummary()

        assert len(summary) == 1
        assert isinstance(summary[0], TypstParagraph)
        expected = "M01测风塔 100m、120m 高度月平均风功率密度 229.4W/m²、229.4W/m²，最大值都出现在 4 月，最小值都出现在 7 月。"
        assert summary[0].text == expected

    def test_disagree_renders_empty_summary(
        self,
        monthly_power_pattern_disagree_atom: SingleMastMonthlyPowerPatternAtom,
    ) -> None:
        """When heights disagree, summary is empty."""
        summary = monthly_power_pattern_disagree_atom.renderSummary()

        assert summary == []


class TestDailyPatternAgreement:
    """Tests for daily pattern agreement behavior."""

    def test_agree_renders_exact_summary_text(
        self,
        daily_pattern_agree_atom: SingleMastDailyPatternAtom,
    ) -> None:
        """When all heights agree, summary contains exact expected text."""
        summary = daily_pattern_agree_atom.renderSummary()

        assert len(summary) == 1
        assert isinstance(summary[0], TypstParagraph)
        expected = "M01测风塔 100m、120m 高度日平均风速最大值都出现在 14 时，最小值都出现在 08 时。"
        assert summary[0].text == expected

    def test_disagree_renders_empty_summary(
        self,
        daily_pattern_disagree_atom: SingleMastDailyPatternAtom,
    ) -> None:
        """When heights disagree, summary is empty."""
        summary = daily_pattern_disagree_atom.renderSummary()

        assert summary == []


class TestDailyPowerPatternAgreement:
    """Tests for daily power pattern agreement behavior."""

    def test_agree_renders_exact_summary_text(
        self,
        daily_power_pattern_agree_atom: SingleMastDailyPowerPatternAtom,
    ) -> None:
        """When all heights agree, summary contains exact expected text."""
        summary = daily_power_pattern_agree_atom.renderSummary()

        assert len(summary) == 1
        assert isinstance(summary[0], TypstParagraph)
        expected = "M01测风塔 100m、120m 高度日平均风功率密度最大值都出现在 14 时，最小值都出现在 08 时。"
        assert summary[0].text == expected

    def test_disagree_renders_empty_summary(
        self,
        daily_power_pattern_disagree_atom: SingleMastDailyPowerPatternAtom,
    ) -> None:
        """When heights disagree, summary is empty."""
        summary = daily_power_pattern_disagree_atom.renderSummary()

        assert summary == []


class TestAllAtoms:
    """Tests that apply to all 6 temporal pattern atoms."""

    @pytest.fixture
    def all_atoms(
        self,
        daily_pattern_atom: SingleMastDailyPatternAtom,
        daily_power_pattern_atom: SingleMastDailyPowerPatternAtom,
        monthly_pattern_atom: SingleMastMonthlyPatternAtom,
        monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom,
        monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom,
        monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom,
    ) -> list[Any]:
        """Return a list of all 6 atom types for testing."""
        return [
            daily_pattern_atom,
            daily_power_pattern_atom,
            monthly_pattern_atom,
            monthly_power_pattern_atom,
            monthly_daily_wind_atom,
            monthly_daily_power_atom,
        ]

    def test_all_atoms_have_mast_name(self, all_atoms: list[Any]) -> None:
        """Verify all atoms have correct mast name in meta."""
        for atom in all_atoms:
            assert atom.meta.mast_name == "M01"

    def test_all_atoms_produce_valid_images(self, all_atoms: list[Any], tmp_path: Path) -> None:
        """Verify all atoms can produce valid PNG images."""
        for atom in all_atoms:
            image_path = atom.renderImage(tmp_path)
            assert image_path.exists()
            assert image_path.suffix == ".png"
            assert image_path.stat().st_size > 100

    def test_all_atoms_have_consistent_hashes(self, all_atoms: list[Any]) -> None:
        """Verify all atoms produce consistent hashes."""
        for atom in all_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2
            assert len(hash1) > 0

    def test_image_caching(self, all_atoms: list[Any], tmp_path: Path) -> None:
        """Verify images are cached and not regenerated when they exist."""
        for atom in all_atoms:
            path1 = atom.renderImage(tmp_path)
            mtime1 = path1.stat().st_mtime

            path2 = atom.renderImage(tmp_path)
            mtime2 = path2.stat().st_mtime

            assert path1 == path2
            assert mtime1 == mtime2

    def test_force_regenerate(self, all_atoms: list[Any], tmp_path: Path) -> None:
        """Verify force=True regenerates images even if they exist."""
        for atom in all_atoms:
            path1 = atom.renderImage(tmp_path)

            import time
            time.sleep(0.01)
            path2 = atom.renderImage(tmp_path, force=True)

            assert path1 == path2
            assert path2.exists()
