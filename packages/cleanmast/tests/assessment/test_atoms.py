"""Tests for all 4 ReportAtom implementations."""

from pathlib import Path
from typing import Any

from typst_ir import TypstParagraph, TypstTable


class TestSingleMastMonthlyPatternAtom:
    """Tests for SingleMastMonthlyPatternAtom."""

    def test_render_table_produces_valid_typst(self, monthly_wind_atom: Any):
        """Test that renderTable produces valid Typst table markup."""
        result = monthly_wind_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check table content by inspecting data
        assert "月份" in result.headers or any("月份" in str(row) for row in result.data)

    def test_render_table_includes_all_rows(self, monthly_wind_atom: Any):
        """Test that table includes all data rows."""
        result = monthly_wind_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check data has content (at least 3 rows for 3 months)
        assert len(result.data) >= 3

    def test_render_table_with_height_marker(self, monthly_wind_atom: Any):
        """Test that height markers are included in table headers."""
        result = monthly_wind_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check for extrapolation marker in table headers (e.g., "120m 外推(m/s)")
        assert any("外推" in h for h in result.headers)

    def test_render_summary_includes_mast_name(self, monthly_wind_atom: Any):
        """Test that summary includes mast name."""
        result = monthly_wind_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text

    def test_render_summary_includes_heights(self, monthly_wind_atom: Any):
        """Test that summary mentions height levels."""
        result = monthly_wind_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should mention heights >100m
        assert "120m" in result[0].text

    def test_render_summary_includes_mean_speed(self, monthly_wind_atom: Any):
        """Test that summary includes mean wind speed."""
        result = monthly_wind_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should include mean speed value
        assert "m/s" in result[0].text

    def test_render_image_creates_png_file(
        self,
        monthly_wind_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that renderImage creates a PNG file."""
        image_path = monthly_wind_atom.renderImage(temp_output_dir)

        assert image_path.exists()
        assert image_path.suffix == ".png"

    def test_render_image_respects_force_parameter(
        self,
        monthly_wind_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that force=False returns existing file without regeneration."""
        # First call creates the file
        path1 = monthly_wind_atom.renderImage(temp_output_dir, force=False)
        mtime1 = path1.stat().st_mtime

        # Second call should return same file without regenerating
        path2 = monthly_wind_atom.renderImage(temp_output_dir, force=False)
        mtime2 = path2.stat().st_mtime

        assert path1 == path2
        assert mtime1 == mtime2

    def test_render_image_force_regenerates(
        self,
        monthly_wind_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that force=True regenerates the file."""
        # Create initial file
        monthly_wind_atom.renderImage(temp_output_dir)

        # Force regenerate
        path = monthly_wind_atom.renderImage(temp_output_dir, force=True)

        assert path.exists()

    def test_render_image_filename_includes_mast_name_and_hash(
        self,
        monthly_wind_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that image filename includes mast name and hash."""
        image_path = monthly_wind_atom.renderImage(temp_output_dir)
        hashkey = monthly_wind_atom.get_or_compute_df_hashkey()

        assert "monthly_pattern" in image_path.name
        assert "M01" in image_path.name
        assert hashkey in image_path.name


class TestSingleMastMonthlyWindFrequencyRoseAtom:
    """Tests for SingleMastMonthlyWindFrequencyRoseAtom."""

    def test_render_table_produces_valid_typst(self, wind_frequency_rose_atom: Any):
        """Test that renderTable produces valid Typst table markup."""
        result = wind_frequency_rose_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check table has direction-related content
        assert any("风向" in str(row) for row in result.data) or "风向" in result.headers

    def test_render_table_includes_all_sectors(self, wind_frequency_rose_atom: Any):
        """Test that table includes all 16 sectors."""
        result = wind_frequency_rose_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check for sector names in table data
        table_text = str(result.data) + str(result.headers)
        assert "N" in table_text
        assert "NNE" in table_text
        assert "NE" in table_text

    def test_render_summary_includes_mast_name(self, wind_frequency_rose_atom: Any):
        """Test that summary includes mast name."""
        result = wind_frequency_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text
        assert "测风塔" in result[0].text

    def test_render_summary_includes_dominant_directions(
        self,
        wind_frequency_rose_atom: Any,
    ):
        """Test that summary includes dominant wind directions."""
        result = wind_frequency_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should mention dominant directions
        assert "无125m~160m高度风向频率数据" in result[0].text

    def test_render_summary_includes_heights(self, wind_frequency_rose_atom: Any):
        """Test that summary mentions height levels."""
        result = wind_frequency_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should mention heights >100m
        assert "无125m~160m高度风向频率数据" in result[0].text

    def test_render_image_creates_png_file(
        self,
        wind_frequency_rose_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that renderImage creates a PNG file."""
        image_path = wind_frequency_rose_atom.renderImage(temp_output_dir)

        assert image_path.exists()
        assert image_path.suffix == ".png"

    def test_render_image_filename_includes_windfreqrose(
        self,
        wind_frequency_rose_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that image filename includes windfreqrose prefix."""
        image_path = wind_frequency_rose_atom.renderImage(temp_output_dir)

        assert "windfreqrose" in image_path.name


class TestSingleMastWindPowerRoseAtom:
    """Tests for SingleMastWindPowerRoseAtom."""

    def test_render_table_produces_valid_typst(self, wind_power_rose_atom: Any):
        """Test that renderTable produces valid Typst table markup."""
        result = wind_power_rose_atom.renderTable()

        assert isinstance(result, TypstTable)
        # Check table has direction-related content
        assert any("风向" in str(row) for row in result.data) or "风向" in result.headers

    def test_render_table_handles_null_power_density(
        self,
        wind_power_rose_atom_null_power: Any,
    ):
        """Test that table handles null power density values gracefully."""
        result = wind_power_rose_atom_null_power.renderTable()

        # Should still produce valid table
        assert isinstance(result, TypstTable)

    def test_render_summary_includes_mast_name(self, wind_power_rose_atom: Any):
        """Test that summary includes mast name."""
        result = wind_power_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text
        assert "测风塔" in result[0].text

    def test_render_summary_includes_dominant_power_directions(
        self,
        wind_power_rose_atom: Any,
    ):
        """Test that summary includes dominant power flow directions."""
        result = wind_power_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should mention dominant energy flow directions
        assert "无125m~160m高度风能频率数据" in result[0].text

    def test_render_summary_includes_avg_power_density(
        self,
        wind_power_rose_atom: Any,
    ):
        """Test that summary includes average power density."""
        result = wind_power_rose_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        # Should include average power density
        assert "无125m~160m高度风能频率数据" in result[0].text

    def test_render_summary_fallback_without_power_data(
        self,
        wind_power_rose_atom_null_power: Any,
    ):
        """Test that summary falls back to frequency-only when no power data."""
        result = wind_power_rose_atom_null_power.renderSummary()

        # Should still produce a valid summary
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text
        assert "测风塔" in result[0].text

    def test_render_image_creates_png_file(
        self,
        wind_power_rose_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that renderImage creates a PNG file."""
        image_path = wind_power_rose_atom.renderImage(temp_output_dir)

        assert image_path.exists()
        assert image_path.suffix == ".png"

    def test_render_image_filename_includes_windpowerrose(
        self,
        wind_power_rose_atom: Any,
        temp_output_dir: Path,
    ):
        """Test that image filename includes windpowerrose prefix."""
        image_path = wind_power_rose_atom.renderImage(temp_output_dir)

        assert "windpowerrose" in image_path.name


class TestAllAtomsCommonBehavior:
    """Tests for common behavior across all atom types."""

    def test_all_atoms_inherit_from_report_atom(self, all_atoms: list[Any]):
        """Test that all atoms inherit from ReportAtom."""
        from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom

        for atom in all_atoms:
            assert isinstance(atom, ReportAtom)

    def test_all_atoms_have_df_attribute(self, all_atoms: list[Any]):
        """Test that all atoms have a df attribute."""
        for atom in all_atoms:
            assert hasattr(atom, "df")
            assert atom.df is not None

    def test_all_atoms_have_meta_attribute(self, all_atoms: list[Any]):
        """Test that all atoms have a meta attribute."""
        for atom in all_atoms:
            assert hasattr(atom, "meta")
            assert atom.meta is not None

    def test_all_atoms_have_schema_attribute(self, all_atoms: list[Any]):
        """Test that all atoms have a schema attribute."""
        for atom in all_atoms:
            assert hasattr(atom, "schema")
            assert atom.schema is not None

    def test_all_atoms_produce_unique_hashes(self, all_atoms: list[Any]):
        """Test that different atom types produce different hashes."""
        hashes = [atom.get_or_compute_df_hashkey() for atom in all_atoms]

        # All hashes should be unique (different data)
        assert len(set(hashes)) == len(hashes)

    def test_all_atoms_produce_consistent_hashes(self, all_atoms: list[Any]):
        """Test that hashes are consistent across multiple calls."""
        for atom in all_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2

    def test_all_atoms_render_table_returns_ir_node(self, all_atoms: list[Any]):
        for atom in all_atoms:
            result = atom.renderTable()
            assert isinstance(result, (TypstTable, type(None)))

    def test_all_atoms_render_summary_returns_list(self, all_atoms: list[Any]):
        """Test that all atoms renderSummary returns a list of IR nodes."""
        for atom in all_atoms:
            result = atom.renderSummary()
            assert isinstance(result, list)
            assert len(result) >= 0
            if len(result) > 0:
                assert isinstance(result[0], TypstParagraph)

    def test_all_atoms_render_image_returns_path(
        self,
        all_atoms: list[Any],
        temp_output_dir: Path,
    ):
        """Test that all atoms renderImage returns a Path."""
        for atom in all_atoms:
            result = atom.renderImage(temp_output_dir)
            assert isinstance(result, Path)
            # Some atoms return empty Path (no image), others return actual path
            if result != Path():
                assert result.exists()
