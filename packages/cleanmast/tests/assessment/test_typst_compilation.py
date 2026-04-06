"""Typst compilation validation tests for report atoms."""

import shutil
import subprocess
from pathlib import Path

import pytest

TYPST_AVAILABLE = shutil.which("typst") is not None


@pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
class TestTypstCompilation:
    """Test that atom renderTable() output compiles with Typst."""

    def compile_typst(self, typ_content: str, output_path: Path) -> tuple[bool, str]:
        """Compile Typst content to PDF."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temp_typ_file = output_path.with_suffix(".typ")
        temp_typ_file.write_text(typ_content, encoding="utf-8")

        try:
            result = subprocess.run(
                ["typst", "compile", str(temp_typ_file), str(output_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, ""
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Compilation timed out after 30 seconds"
        except Exception as e:
            return False, f"Compilation failed with exception: {e}"

    def compare_with_snapshot(self, atom_name: str, generated_content: str) -> None:
        """Compare generated Typst content with golden snapshot."""
        snapshot_path = Path(__file__).parent / "snapshots" / f"{atom_name}.typ"

        if not snapshot_path.exists():
            pytest.skip(f"Snapshot not found: {snapshot_path}")

        expected = snapshot_path.read_text(encoding="utf-8")
        assert generated_content == expected, f"Snapshot mismatch for {atom_name}"

    def test_wind_frequency_rose_compiles(self, wind_frequency_rose_atom, tmp_path):
        """Test wind frequency rose table compiles with Typst."""
        typ_content = wind_frequency_rose_atom.renderTable()
        self.compare_with_snapshot("wind_frequency_rose", typ_content)

        output_pdf = tmp_path / "wind_frequency_rose.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_power_rose_compiles(self, wind_power_rose_atom, tmp_path):
        """Test wind power rose table compiles with Typst."""
        typ_content = wind_power_rose_atom.renderTable()
        self.compare_with_snapshot("wind_power_rose", typ_content)

        output_pdf = tmp_path / "wind_power_rose.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_monthly_wind_compiles(self, monthly_wind_atom, tmp_path):
        """Test monthly wind speed table compiles with Typst."""
        typ_content = monthly_wind_atom.renderTable()

        output_pdf = tmp_path / "monthly_wind.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_monthly_wind_power_compiles(self, monthly_wind_power_atom, tmp_path):
        """Test monthly wind power density table compiles with Typst."""
        typ_content = monthly_wind_power_atom.renderTable()

        output_pdf = tmp_path / "monthly_wind_power.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_turbulence_intensity_compiles(self, turbulence_intensity_atom, tmp_path):
        """Test turbulence intensity table compiles with Typst."""
        typ_content = turbulence_intensity_atom.renderTable()

        output_pdf = tmp_path / "turbulence_intensity.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_turbulence_sector_compiles(self, turbulence_sector_atom, tmp_path):
        """Test turbulence sector table compiles with Typst."""
        typ_content = turbulence_sector_atom.renderTable()
        self.compare_with_snapshot("turbulence_sector", typ_content)

        output_pdf = tmp_path / "turbulence_sector.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_turbulence_summary_compiles(self, turbulence_summary_atom, tmp_path):
        """Test turbulence summary table compiles with Typst."""
        typ_content = turbulence_summary_atom.renderTable()

        output_pdf = tmp_path / "turbulence_summary.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_weibull_distribution_compiles(self, weibull_distribution_atom, tmp_path):
        """Test Weibull distribution table compiles with Typst."""
        typ_content = weibull_distribution_atom.renderTable()
        self.compare_with_snapshot("weibull_distribution", typ_content)

        output_pdf = tmp_path / "weibull_distribution.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_weibull_parameters_compiles(self, weibull_parameters_atom, tmp_path):
        """Test Weibull parameters table compiles with Typst."""
        typ_content = weibull_parameters_atom.renderTable()

        output_pdf = tmp_path / "weibull_parameters.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_weibull_multi_compiles(self, weibull_multi_atom, tmp_path):
        """Test Weibull multi-height table compiles with Typst."""
        typ_content = weibull_multi_atom.renderTable()

        output_pdf = tmp_path / "weibull_multi.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_vertical_profile_compiles(self, vertical_profile_atom, tmp_path):
        """Test vertical profile table compiles with Typst."""
        typ_content = vertical_profile_atom.renderTable()
        self.compare_with_snapshot("vertical_profile", typ_content)

        output_pdf = tmp_path / "vertical_profile.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_shear_table_compiles(self, wind_shear_table_atom, tmp_path):
        """Test wind shear table compiles with Typst."""
        typ_content = wind_shear_table_atom.renderTable()

        output_pdf = tmp_path / "wind_shear_table.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_shear_matrix_compiles(self, wind_shear_matrix_atom, tmp_path):
        """Test wind shear matrix compiles with Typst."""
        typ_content = wind_shear_matrix_atom.renderTable()

        output_pdf = tmp_path / "wind_shear_matrix.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    @pytest.mark.xfail(reason="Entity generates invalid Typst syntax with double brackets")
    def test_wind_frequency_table_compiles(self, wind_frequency_table_atom, tmp_path):
        """Test wind frequency table compiles with Typst."""
        typ_content = wind_frequency_table_atom.renderTable()

        output_pdf = tmp_path / "wind_frequency_table.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    @pytest.mark.xfail(reason="Entity generates invalid Typst syntax with double brackets")
    def test_wind_power_frequency_table_compiles(self, wind_power_frequency_table_atom, tmp_path):
        """Test wind power frequency table compiles with Typst."""
        typ_content = wind_power_frequency_table_atom.renderTable()

        output_pdf = tmp_path / "wind_power_frequency_table.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_range_summary_compiles(self, wind_range_summary_atom, tmp_path):
        """Test wind range summary table compiles with Typst."""
        typ_content = wind_range_summary_atom.renderTable()

        output_pdf = tmp_path / "wind_range_summary.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_rose_grid_compiles(self, wind_rose_grid_atom, tmp_path):
        """Test wind rose grid table compiles with Typst."""
        typ_content = wind_rose_grid_atom.renderTable()

        output_pdf = tmp_path / "wind_rose_grid.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_daily_pattern_compiles(self, daily_pattern_atom, tmp_path):
        """Test daily pattern table compiles with Typst."""
        typ_content = daily_pattern_atom.renderTable()

        output_pdf = tmp_path / "daily_pattern.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_daily_power_pattern_compiles(self, daily_power_pattern_atom, tmp_path):
        """Test daily power pattern table compiles with Typst."""
        typ_content = daily_power_pattern_atom.renderTable()

        output_pdf = tmp_path / "daily_power_pattern.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_monthly_daily_wind_compiles(self, monthly_daily_wind_atom, tmp_path):
        """Test monthly daily wind table compiles with Typst."""
        typ_content = monthly_daily_wind_atom.renderTable()

        output_pdf = tmp_path / "monthly_daily_wind.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_monthly_daily_power_compiles(self, monthly_daily_power_atom, tmp_path):
        """Test monthly daily power table compiles with Typst."""
        typ_content = monthly_daily_power_atom.renderTable()

        output_pdf = tmp_path / "monthly_daily_power.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"

    def test_wind_timeseries_compiles(self, wind_timeseries_atom, tmp_path):
        """Test wind timeseries table compiles with Typst."""
        typ_content = wind_timeseries_atom.renderTable()

        output_pdf = tmp_path / "wind_timeseries.pdf"
        success, error_msg = self.compile_typst(typ_content, output_pdf)

        assert success, f"Typst compilation failed: {error_msg}"
        assert output_pdf.exists(), "PDF output file was not created"
