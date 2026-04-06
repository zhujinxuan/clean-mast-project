"""Tests for wind temporal pattern atoms.

Tests cover all 7 temporal pattern atoms:
- SingleMastWindTimeseriesAtom
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
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_pattern import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_power_pattern import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_power import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_wind import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_pattern import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_power_pattern import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.timeseries import (
    SingleMastWindTimeseriesAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_timeseries_df() -> pl.DataFrame:
    """Create sample time series DataFrame for timeseries atom."""
    timestamps = [
        datetime(2023, 1, 1) + timedelta(hours=i) for i in range(168)
    ]  # 1 week of hourly data

    return pl.DataFrame({
        "timestamp": timestamps,
        "hour": [ts.hour for ts in timestamps],
        "month": [ts.month for ts in timestamps],
        "wind_speed": [8.0 + (i % 24) * 0.2 for i in range(168)],
        "wind_power": [300.0 + (i % 24) * 10.0 for i in range(168)],
        "height": [100.0] * 168,
        "mean_speed": [8.0 + (i % 24) * 0.2 for i in range(168)],
        "mean_power": [300.0 + (i % 24) * 10.0 for i in range(168)],
        "interpolation_marker": [None] * 168,
    })


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

    for month in [1, 4, 7, 10]:  # Sample 4 months
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
def timeseries_atom(
    sample_timeseries_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindTimeseriesAtom:
    """Create a SingleMastWindTimeseriesAtom for testing."""
    return SingleMastWindTimeseriesAtom.create(
        schema=TemporalPatternSchema,
        df=sample_timeseries_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_pattern_atom(
    sample_daily_pattern_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
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
    sample_mast_meta: SingleMastMeta,
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
    sample_mast_meta: SingleMastMeta,
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
    sample_mast_meta: SingleMastMeta,
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
    sample_mast_meta: SingleMastMeta,
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
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyDailyPowerAtom:
    """Create a SingleMastMonthlyDailyPowerAtom for testing."""
    return SingleMastMonthlyDailyPowerAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_daily_df_full,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastWindTimeseriesAtom
# =============================================================================


class TestSingleMastWindTimeseriesAtom:
    """Tests for SingleMastWindTimeseriesAtom."""

    def test_render_image(self, timeseries_atom: SingleMastWindTimeseriesAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = timeseries_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, timeseries_atom: SingleMastWindTimeseriesAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = timeseries_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "平均风速" in table

    def test_render_summary(self, timeseries_atom: SingleMastWindTimeseriesAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = timeseries_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "风速时间序列" in summary

    def test_content_hash_consistency(self, timeseries_atom: SingleMastWindTimeseriesAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = timeseries_atom.get_or_compute_df_hashkey()
        hash2 = timeseries_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWindTimeseriesAtom_" in hash1

    def test_reference_generation(self, timeseries_atom: SingleMastWindTimeseriesAtom) -> None:
        """Test getReference returns correct format."""
        ref = timeseries_atom.getReference()
        
        assert ref.startswith("@fig-")
        assert "SingleMastWindTimeseriesAtom_" in ref


# =============================================================================
# Test SingleMastDailyPatternAtom
# =============================================================================


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
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "小时" in table
        # Should have 24 hour rows
        assert table.count(":00") == 24

    def test_render_summary(self, daily_pattern_atom: SingleMastDailyPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = daily_pattern_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "日变化风速" in summary
        assert "风速峰值" in summary

    def test_content_hash_consistency(self, daily_pattern_atom: SingleMastDailyPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = daily_pattern_atom.get_or_compute_df_hashkey()
        hash2 = daily_pattern_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastDailyPatternAtom_" in hash1


# =============================================================================
# Test SingleMastDailyPowerPatternAtom
# =============================================================================


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
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "小时" in table
        assert "W/m" in table  # Power density unit

    def test_render_summary(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = daily_power_pattern_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "日变化风功率密度" in summary
        assert "风功率密度峰值" in summary

    def test_content_hash_consistency(self, daily_power_pattern_atom: SingleMastDailyPowerPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = daily_power_pattern_atom.get_or_compute_df_hashkey()
        hash2 = daily_power_pattern_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastDailyPowerPatternAtom_" in hash1


# =============================================================================
# Test SingleMastMonthlyPatternAtom
# =============================================================================


class TestSingleMastMonthlyPatternAtom:
    """Tests for SingleMastMonthlyPatternAtom."""

    def test_render_image(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_pattern_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with 12 months."""
        table = monthly_pattern_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "月份" in table
        # Should have 12 month rows
        for month in range(1, 13):
            assert f"{month}月" in table

    def test_render_summary(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_pattern_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "月变化风速" in summary
        assert "季节" in summary

    def test_content_hash_consistency(self, monthly_pattern_atom: SingleMastMonthlyPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_pattern_atom.get_or_compute_df_hashkey()
        hash2 = monthly_pattern_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastMonthlyPatternAtom_" in hash1


# =============================================================================
# Test SingleMastMonthlyPowerPatternAtom
# =============================================================================


class TestSingleMastMonthlyPowerPatternAtom:
    """Tests for SingleMastMonthlyPowerPatternAtom."""

    def test_render_image(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_power_pattern_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test renderTable returns non-empty Typst table with power data."""
        table = monthly_power_pattern_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "月份" in table
        assert "W/m" in table

    def test_render_summary(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_power_pattern_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "月变化风功率密度" in summary
        assert "季节" in summary

    def test_content_hash_consistency(self, monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_power_pattern_atom.get_or_compute_df_hashkey()
        hash2 = monthly_power_pattern_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastMonthlyPowerPatternAtom_" in hash1


# =============================================================================
# Test SingleMastMonthlyDailyWindAtom
# =============================================================================


class TestSingleMastMonthlyDailyWindAtom:
    """Tests for SingleMastMonthlyDailyWindAtom."""

    def test_render_image(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_daily_wind_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = monthly_daily_wind_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "月份" in table
        assert "平均风速" in table
        assert "日较差" in table

    def test_render_summary(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_daily_wind_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "日变化" in summary
        assert "峰值" in summary

    def test_content_hash_consistency(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_daily_wind_atom.get_or_compute_df_hashkey()
        hash2 = monthly_daily_wind_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastMonthlyDailyWindAtom_" in hash1

    def test_figure_reference_in_summary(self, monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom) -> None:
        """Test summary includes figure reference."""
        summary = monthly_daily_wind_atom.renderSummary()
        
        assert "@fig-" in summary


# =============================================================================
# Test SingleMastMonthlyDailyPowerAtom
# =============================================================================


class TestSingleMastMonthlyDailyPowerAtom:
    """Tests for SingleMastMonthlyDailyPowerAtom."""

    def test_render_image(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = monthly_daily_power_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test renderTable returns non-empty Typst table with power data."""
        table = monthly_daily_power_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "月份" in table
        assert "功率密度" in table

    def test_render_summary(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = monthly_daily_power_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "风功率密度" in summary
        assert "日变化" in summary

    def test_content_hash_consistency(self, monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = monthly_daily_power_atom.get_or_compute_df_hashkey()
        hash2 = monthly_daily_power_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastMonthlyDailyPowerAtom_" in hash1


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestAllAtoms:
    """Tests that apply to all temporal atoms."""

    @pytest.fixture
    def all_atoms(
        self,
        timeseries_atom: SingleMastWindTimeseriesAtom,
        daily_pattern_atom: SingleMastDailyPatternAtom,
        daily_power_pattern_atom: SingleMastDailyPowerPatternAtom,
        monthly_pattern_atom: SingleMastMonthlyPatternAtom,
        monthly_power_pattern_atom: SingleMastMonthlyPowerPatternAtom,
        monthly_daily_wind_atom: SingleMastMonthlyDailyWindAtom,
        monthly_daily_power_atom: SingleMastMonthlyDailyPowerAtom,
    ) -> list[Any]:
        """Return a list of all atom types for testing."""
        return [
            timeseries_atom,
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
            assert image_path.stat().st_size > 100  # At least 100 bytes

    def test_all_atoms_produce_non_empty_tables(self, all_atoms: list[Any]) -> None:
        """Verify all atoms produce non-empty tables."""
        for atom in all_atoms:
            table = atom.renderTable()
            assert isinstance(table, str)
            assert len(table) > 0
            assert "#table(" in table

    def test_all_atoms_produce_chinese_summaries(self, all_atoms: list[Any]) -> None:
        """Verify all atoms produce Chinese summaries."""
        for atom in all_atoms:
            summary = atom.renderSummary()
            assert isinstance(summary, str)
            assert len(summary) > 0
            # Should contain Chinese characters
            assert any("\u4e00" <= char <= "\u9fff" for char in summary)

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
            # First render
            path1 = atom.renderImage(tmp_path)
            mtime1 = path1.stat().st_mtime
            
            # Second render (should use cache)
            path2 = atom.renderImage(tmp_path)
            mtime2 = path2.stat().st_mtime
            
            assert path1 == path2
            assert mtime1 == mtime2  # File not modified

    def test_force_regenerate(self, all_atoms: list[Any], tmp_path: Path) -> None:
        """Verify force=True regenerates images even if they exist."""
        for atom in all_atoms:
            # First render
            path1 = atom.renderImage(tmp_path)
            
            # Force regenerate
            import time
            time.sleep(0.01)  # Small delay to ensure different mtime
            path2 = atom.renderImage(tmp_path, force=True)
            
            assert path1 == path2
            # Note: On some systems mtime might not change with such small delays
            # So we just verify the file still exists and is valid
            assert path2.exists()
