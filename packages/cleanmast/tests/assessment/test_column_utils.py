"""Tests for column_utils module."""

from cleanmast.subdomains.assessment.domain.value_objects.report_meta import (
    detect_interpolation_marker,
)


class TestDetectInterpolationMarker:
    """Tests for detect_interpolation_marker function."""

    def test_extrapolated_marker(self):
        """Test detection of extrapolated marker."""
        result = detect_interpolation_marker("WS_120m_fill:extrapolated")

        assert result == "外推"

    def test_interpolated_marker(self):
        """Test detection of interpolated marker."""
        result = detect_interpolation_marker("WS_90m_fill:interpolated")

        assert result == "内插"

    def test_no_marker(self):
        """Test with no fill marker."""
        result = detect_interpolation_marker("WS_100m_avg")

        assert result == ""

    def test_unknown_marker(self):
        """Test with unknown fill type."""
        result = detect_interpolation_marker("WS_100m_fill:unknown")

        assert result == ""  # Returns empty string for unknown types

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        result1 = detect_interpolation_marker("WS_100m_fill:EXTRAPOLATED")
        result2 = detect_interpolation_marker("WS_100m_fill:Extrapolated")

        assert result1 == "外推"
        assert result2 == "外推"
