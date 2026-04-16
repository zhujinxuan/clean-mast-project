"""Tests for simplified wind frequency report atoms.

Tests cover 4 new simplified wind frequency atoms:
- SingleMastWindFrequencyHoursAtom
- SingleMastWindPowerHoursAtom
- SingleMastWindProductiveRangeAtom
- SingleMastWindDistributionSubgridAtom
"""

from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_distribution_subgrid import (
    SingleMastWindDistributionSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_hours import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_hours import (
    SingleMastWindPowerHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_productive_range import (
    SingleMastWindProductiveRangeAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)
from typst_ir import TypstParagraph, TypstTable

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_frequency_df_with_interested_heights() -> pl.DataFrame:
    """Create sample wind frequency data with interested and non-interested heights.

    Interested heights are >120m and ≤160m.
    Includes 100m (not interested), 130m (interested), 140m (interested), 150m (interested).
    """
    rows = []

    for height in [100.0, 130.0, 140.0, 150.0]:
        marker = "外推" if height > 140 else None
        speed_shift = (height - 100) * 0.02

        for bin_idx in range(29):
            bin_start = float(bin_idx)
            bin_end = float(bin_idx + 1) if bin_idx < 28 else 100.0
            bin_center = bin_start + 0.5

            effective_center = bin_center - speed_shift

            if effective_center < 6:
                freq = 0.02 + effective_center * 0.015
            elif effective_center < 10:
                freq = 0.12 - (effective_center - 8) * 0.01
            else:
                freq = max(0.02 - (effective_center - 10) * 0.002, 0.001)

            occurrence_hours = freq * 8760.0

            power_factor = bin_center ** 3
            p_freq = freq * power_factor

            rows.append({
                "height": height,
                "interpolation_marker": marker,
                "bin_start": bin_start,
                "bin_end": bin_end,
                "bin_center": bin_center,
                "frequency": freq,
                "occurrence_hours": occurrence_hours,
                "power_frequency": p_freq,
                "power_hours": p_freq * 8760.0,
            })

        # Normalize per height
        height_rows = [r for r in rows if r["height"] == height]
        total_freq = sum(r["frequency"] for r in height_rows)
        total_power_freq = sum(r["power_frequency"] for r in height_rows)

        for r in height_rows:
            r["frequency"] = r["frequency"] / total_freq
            r["occurrence_hours"] = r["frequency"] * 8760.0
            r["power_frequency"] = r["power_frequency"] / total_power_freq
            r["power_hours"] = r["power_frequency"] * 8760.0

    return pl.DataFrame(rows)


@pytest.fixture
def wind_frequency_hours_atom(
    sample_wind_frequency_df_with_interested_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindFrequencyHoursAtom:
    """Create a SingleMastWindFrequencyHoursAtom for testing."""
    return SingleMastWindFrequencyHoursAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_with_interested_heights,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_hours_atom(
    sample_wind_frequency_df_with_interested_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindPowerHoursAtom:
    """Create a SingleMastWindPowerHoursAtom for testing."""
    return SingleMastWindPowerHoursAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_with_interested_heights,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_productive_range_atom(
    sample_wind_frequency_df_with_interested_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindProductiveRangeAtom:
    """Create a SingleMastWindProductiveRangeAtom for testing."""
    return SingleMastWindProductiveRangeAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_with_interested_heights,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_distribution_subgrid_atom(
    sample_wind_frequency_df_with_interested_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindDistributionSubgridAtom:
    """Create a SingleMastWindDistributionSubgridAtom for testing."""
    return SingleMastWindDistributionSubgridAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_with_interested_heights,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastWindFrequencyHoursAtom
# =============================================================================


class TestSingleMastWindFrequencyHoursAtom:
    """Tests for SingleMastWindFrequencyHoursAtom."""

    def test_render_table_structure(self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom) -> None:
        """Test renderTable has 0-28 m/s bins as rows and interested heights as paired columns."""
        table = wind_frequency_hours_atom.renderTable()

        assert isinstance(table, TypstTable)
        # Check headers contain interested heights only (>120m, ≤160m) with 频率/出现小时数 suffixes
        headers_text = " ".join(table.headers)
        assert "130m 频率" in headers_text
        assert "130m 出现小时数" in headers_text
        assert "140m" in headers_text or "140m(外推)" in headers_text
        assert "150m(外推) 频率" in headers_text
        assert "100m" not in headers_text

        # Check data has 25 rows for bins 0-24 (up to 25 m/s)
        assert len(table.data) == 25

        # Each row: 风速区间 + 2 columns per interested height (frequency + hours)
        for row in table.data:
            assert len(row) == 1 + 2 * 3

    def test_render_table_values_have_frequency_and_hours(
        self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom
    ) -> None:
        """Test table cell values alternate between % frequency and integer hours."""
        table = wind_frequency_hours_atom.renderTable()

        assert isinstance(table, TypstTable)
        for row in table.data:
            # Even-indexed height cells (0-based within height cells) should be percentages
            # Odd-indexed should be integer hours
            for idx, cell in enumerate(row[1:]):
                if idx % 2 == 0:
                    assert "%" in cell
                else:
                    assert "%" not in cell
                    assert int(cell) > 0

    def test_render_table_bin_rows(self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom) -> None:
        """Test rows cover 0-25 m/s bins in 1 m/s increments as ranges."""
        table = wind_frequency_hours_atom.renderTable()

        assert isinstance(table, TypstTable)
        bin_ranges = [row[0] for row in table.data]
        assert bin_ranges[0] == "0-1"
        assert bin_ranges[1] == "1-2"
        assert bin_ranges[-1] == "24-25"
        assert len(bin_ranges) == 25

    def test_render_summary(self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom) -> None:
        """Test renderSummary returns Chinese text summarizing 3~25 m/s frequency and hours."""
        summary = wind_frequency_hours_atom.renderSummary()

        assert isinstance(summary, list)
        assert len(summary) > 0
        assert isinstance(summary[0], TypstParagraph)
        summary_text = summary[0].text
        # Expected format: "M01测风塔在130m、140m、150m(外推)测风年数据有效风速（3m/s~25m/s）出现小时数（频率）为{hours} ({freq%}), {hours} ({freq%}), {hours} ({freq%})小时。"
        assert summary_text == (
            "M01测风塔在130m、140m、150m(外推)测风年数据有效风速（3m/s~25m/s）出现小时数（频率）为"
            "7853 (89.6%), 7923 (90.4%), 7995 (91.3%)小时。"
        )

    def test_render_image(self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom, tmp_path: Path) -> None:
        """Test renderImage returns empty Path (no image for hours table)."""
        image_path = wind_frequency_hours_atom.renderImage(tmp_path)
        assert image_path == Path()

    def test_caption_properties(self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom) -> None:
        assert wind_frequency_hours_atom.default_image_caption is None
        assert wind_frequency_hours_atom.default_table_caption == "M01 各风速区间风速频率和出现小时数"

    def test_content_hash_consistency(
        self, wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_frequency_hours_atom.get_or_compute_df_hashkey()
        hash2 = wind_frequency_hours_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert "SingleMastWindFrequencyHoursAtom_" in hash1


# =============================================================================
# Test SingleMastWindPowerHoursAtom
# =============================================================================


class TestSingleMastWindPowerHoursAtom:
    """Tests for SingleMastWindPowerHoursAtom."""

    def test_render_table_structure(self, wind_power_hours_atom: SingleMastWindPowerHoursAtom) -> None:
        """Test renderTable has same bin structure with paired power freq/hours columns."""
        table = wind_power_hours_atom.renderTable()

        assert isinstance(table, TypstTable)
        # 25 rows for bins 0-24 (up to 25 m/s)
        assert len(table.data) == 25

        headers_text = " ".join(table.headers)
        assert "130m 风能频率" in headers_text
        assert "130m 风能出现小时数" in headers_text
        assert "150m(外推) 风能频率" in headers_text
        assert "100m" not in headers_text

    def test_render_table_values_have_power_frequency_and_hours(
        self, wind_power_hours_atom: SingleMastWindPowerHoursAtom
    ) -> None:
        """Test table cell values alternate between % power frequency and integer hours."""
        table = wind_power_hours_atom.renderTable()

        assert isinstance(table, TypstTable)
        for row in table.data:
            for idx, cell in enumerate(row[1:]):
                if idx % 2 == 0:
                    assert "%" in cell
                else:
                    assert "%" not in cell
                    assert int(cell) >= 0

    def test_render_summary(self, wind_power_hours_atom: SingleMastWindPowerHoursAtom) -> None:
        """Test renderSummary returns empty list for table-only atom."""
        summary = wind_power_hours_atom.renderSummary()
        assert summary == []

    def test_render_image(self, wind_power_hours_atom: SingleMastWindPowerHoursAtom, tmp_path: Path) -> None:
        """Test renderImage returns empty Path (no image for power hours table)."""
        image_path = wind_power_hours_atom.renderImage(tmp_path)
        assert image_path == Path()

    def test_caption_properties(self, wind_power_hours_atom: SingleMastWindPowerHoursAtom) -> None:
        assert wind_power_hours_atom.default_image_caption is None
        assert wind_power_hours_atom.default_table_caption == "M01 各风速区间风能频率和出现小时数"

    def test_content_hash_consistency(
        self, wind_power_hours_atom: SingleMastWindPowerHoursAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_power_hours_atom.get_or_compute_df_hashkey()
        hash2 = wind_power_hours_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert "SingleMastWindPowerHoursAtom_" in hash1


# =============================================================================
# Test SingleMastWindProductiveRangeAtom
# =============================================================================


class TestSingleMastWindProductiveRangeAtom:
    """Tests for SingleMastWindProductiveRangeAtom."""

    def test_render_table_structure(self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom) -> None:
        """Test renderTable has one row per interested height with correct columns."""
        table = wind_productive_range_atom.renderTable()

        assert isinstance(table, TypstTable)
        # Columns should be: 高度(m), 风速出现小时数, 风能出现小时数
        headers_text = " ".join(table.headers)
        assert "高度(m)" in headers_text or "高度" in headers_text
        assert "风速出现小时数" in headers_text
        assert "风能出现小时数" in headers_text

        # One row per interested height
        assert len(table.data) == 3

    def test_render_table_values_are_summed_3_25_hours(
        self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom
    ) -> None:
        """Test values are summed hours for bins 3-25 m/s."""
        table = wind_productive_range_atom.renderTable()

        assert isinstance(table, TypstTable)
        for row in table.data:
            # Each row: height, occurrence_hours, power_hours
            assert len(row) == 3
            occurrence_hours = int(row[1])
            power_hours = int(row[2])
            assert occurrence_hours > 0
            assert power_hours > 0

    def test_render_image(self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom, tmp_path: Path) -> None:
        """Test renderImage returns empty Path (no image for productive range table)."""
        image_path = wind_productive_range_atom.renderImage(tmp_path)
        assert image_path == Path()

    def test_render_summary(self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom) -> None:
        """Test renderSummary returns empty list for table-only atom."""
        summary = wind_productive_range_atom.renderSummary()
        assert summary == []

    def test_caption_properties(self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom) -> None:
        assert wind_productive_range_atom.default_image_caption is None
        assert wind_productive_range_atom.default_table_caption == "M01 有效风速范围(3~25m/s)统计表"

    def test_content_hash_consistency(
        self, wind_productive_range_atom: SingleMastWindProductiveRangeAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_productive_range_atom.get_or_compute_df_hashkey()
        hash2 = wind_productive_range_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert "SingleMastWindProductiveRangeAtom_" in hash1


# =============================================================================
# Test SingleMastWindDistributionSubgridAtom
# =============================================================================


class TestSingleMastWindDistributionSubgridAtom:
    """Tests for SingleMastWindDistributionSubgridAtom."""

    def test_render_image(self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom, tmp_path: Path) -> None:
        """Test renderImage creates a valid PNG file."""
        image_path = wind_distribution_subgrid_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom) -> None:
        """Test renderTable returns None (image-only atom)."""
        table = wind_distribution_subgrid_atom.renderTable()
        assert table is None

    def test_render_summary(self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom) -> None:
        """Test renderSummary returns empty list for image-only atom."""
        summary = wind_distribution_subgrid_atom.renderSummary()
        assert summary == []

    def test_caption_properties(self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom) -> None:
        assert wind_distribution_subgrid_atom.default_image_caption == "M01 各高度风速频率和风能频率"
        assert wind_distribution_subgrid_atom.default_table_caption is None

    def test_content_hash_consistency(
        self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_distribution_subgrid_atom.get_or_compute_df_hashkey()
        hash2 = wind_distribution_subgrid_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert "SingleMastWindDistributionSubgridAtom_" in hash1

    def test_image_caching(
        self, wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom, tmp_path: Path
    ) -> None:
        """Verify images are cached."""
        path1 = wind_distribution_subgrid_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime

        path2 = wind_distribution_subgrid_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime

        assert path1 == path2
        assert mtime1 == mtime2


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestAllWindFrequencyAtoms:
    """Tests that apply to all simplified wind frequency atoms."""

    @pytest.fixture
    def all_wind_frequency_atoms(
        self,
        wind_frequency_hours_atom: SingleMastWindFrequencyHoursAtom,
        wind_power_hours_atom: SingleMastWindPowerHoursAtom,
        wind_productive_range_atom: SingleMastWindProductiveRangeAtom,
        wind_distribution_subgrid_atom: SingleMastWindDistributionSubgridAtom,
    ) -> list[Any]:
        """Return a list of all wind frequency atom types for testing."""
        return [
            wind_frequency_hours_atom,
            wind_power_hours_atom,
            wind_productive_range_atom,
            wind_distribution_subgrid_atom,
        ]

    def test_all_atoms_have_mast_name(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms have correct mast name in meta."""
        for atom in all_wind_frequency_atoms:
            assert atom.meta.mast_name == "M01"

    def test_all_atoms_have_consistent_hashes(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms produce consistent hashes."""
        for atom in all_wind_frequency_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2
            assert len(hash1) > 0

    def test_summary_output_is_list_of_paragraphs(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms return a list from renderSummary."""
        for atom in all_wind_frequency_atoms:
            summary = atom.renderSummary()
            assert isinstance(summary, list)
            if len(summary) > 0:
                assert isinstance(summary[0], TypstParagraph)
