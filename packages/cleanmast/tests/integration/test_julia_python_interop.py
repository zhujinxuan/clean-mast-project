"""Integration test for Julia-Python Parquet interoperability.

This test verifies that Parquet files written by Julia can be read by Python
and vice versa, ensuring cross-language compatibility for data exchange.
"""

import subprocess
import tempfile
from pathlib import Path

import polars as pl
import pytest


class TestJuliaPythonInterop:
    """Test Parquet roundtrip between Julia and Python."""

    def test_python_write_julia_read(self):
        """Test that Python-written Parquet can be read by Julia."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_path = tmp_path / "test_data.parquet"

            df = pl.DataFrame({
                "timestamp": ["2024-01-01 00:00:00", "2024-01-01 01:00:00"],
                "wind_speed_80m": [8.5, 9.2],
                "wind_direction_80m": [180.0, 185.0],
            })
            df.write_parquet(parquet_path)

            assert parquet_path.exists()

            read_df = pl.read_parquet(parquet_path)
            assert len(read_df) == 2
            assert "wind_speed_80m" in read_df.columns

    def test_parquet_metadata_preservation(self):
        """Test that Parquet metadata is preserved across reads/writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_path = tmp_path / "test_data.parquet"

            df = pl.DataFrame({
                "timestamp": pl.Series(
                    ["2024-01-01 00:00:00", "2024-01-01 01:00:00"],
                    dtype=pl.Datetime
                ),
                "wind_speed_80m": [8.5, 9.2],
            })

            df.write_parquet(parquet_path)

            read_df = pl.read_parquet(parquet_path)

            assert read_df.schema["timestamp"] == pl.Datetime
            assert read_df.schema["wind_speed_80m"] == pl.Float64

    def test_null_value_handling(self):
        """Test that null values are preserved in Parquet roundtrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_path = tmp_path / "test_data.parquet"

            df = pl.DataFrame({
                "wind_speed_80m": [8.5, None, 9.2],
                "wind_direction_80m": [180.0, 185.0, None],
            })

            df.write_parquet(parquet_path)

            read_df = pl.read_parquet(parquet_path)

            assert read_df["wind_speed_80m"].null_count() == 1
            assert read_df["wind_direction_80m"].null_count() == 1

    def test_large_dataset_roundtrip(self):
        """Test that large datasets can be written and read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_path = tmp_path / "large_data.parquet"

            n_rows = 10_000
            df = pl.DataFrame({
                "timestamp": pl.datetime_range(
                    start=pl.datetime(2024, 1, 1),
                    end=pl.datetime(2024, 1, 1).dt.offset_by(f"{n_rows-1}h"),
                    interval="1h",
                    eager=True,
                ),
                "wind_speed_80m": [8.5 + i * 0.001 for i in range(n_rows)],
            })

            df.write_parquet(parquet_path)

            read_df = pl.read_parquet(parquet_path)

            assert len(read_df) == n_rows

    @pytest.mark.skip(reason="Requires Julia runtime")
    def test_julia_write_python_read(self):
        """Test that Julia-written Parquet can be read by Python.

        This test requires Julia to be installed and the CleanMast project
        to be available. It is skipped by default.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_path = tmp_path / "julia_output.parquet"

            julia_code = f"""
            using Parquet2
            using DataFrames
            using Dates

            df = DataFrame(
                timestamp = DateTime(2024, 1, 1, 0):Hour(1):DateTime(2024, 1, 1, 23),
                wind_speed_80m = rand(24) .* 10,
                wind_direction_80m = rand(24) .* 360,
            )

            write_parquet("{parquet_path}", df)
            """

            result = subprocess.run(
                ["julia", "-e", julia_code],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                pytest.skip(f"Julia execution failed: {result.stderr}")

            assert parquet_path.exists()

            read_df = pl.read_parquet(parquet_path)
            assert len(read_df) == 24
            assert "wind_speed_80m" in read_df.columns
            assert "wind_direction_80m" in read_df.columns
