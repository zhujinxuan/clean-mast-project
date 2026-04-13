"""Tests for report meta module."""


from cleanmast.subdomains.assessment.domain.value_objects import (
    SingleMastMeta,
    detect_interpolation_marker,
    get_height_display_name,
)


class TestSingleMastMeta:
    """Tests for SingleMastMeta dataclass."""

    def test_default_values(self):
        """Test that SingleMastMeta has correct default values."""
        meta = SingleMastMeta(mast_name="M01")

        assert meta.mast_name == "M01"
        assert meta.air_density == 1.225  # Default value
        assert meta.caption is None
        assert meta.width == "80%"

    def test_custom_values(self):
        """Test that SingleMastMeta accepts custom values."""
        meta = SingleMastMeta(
            mast_name="M02",
            air_density=1.18,
            caption="Test Caption",
            width="90%",
        )

        assert meta.mast_name == "M02"
        assert meta.air_density == 1.18
        assert meta.caption == "Test Caption"
        assert meta.width == "90%"

    def test_caption_defaults_to_none(self):
        """Test that caption defaults to None."""
        meta = SingleMastMeta(mast_name="M01")

        assert meta.caption is None

    def test_caption_override(self):
        """Test that caption can be overridden."""
        meta = SingleMastMeta(mast_name="M01", caption="override")

        assert meta.caption == "override"


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


class TestGetHeightDisplayName:
    """Tests for get_height_display_name function."""

    def test_without_marker(self):
        """Test display name without marker."""
        result = get_height_display_name(100.0)

        assert result == "100m"

    def test_with_extrapolated_marker(self):
        """Test display name with extrapolation marker."""
        result = get_height_display_name(120.0, "外推")

        assert result == "120m 外推"

    def test_with_interpolated_marker(self):
        """Test display name with interpolation marker."""
        result = get_height_display_name(90.0, "内插")

        assert result == "90m 内插"

    def test_float_height_converted_to_int(self):
        """Test that float heights are displayed as integers."""
        result = get_height_display_name(100.7)

        assert result == "100m"


