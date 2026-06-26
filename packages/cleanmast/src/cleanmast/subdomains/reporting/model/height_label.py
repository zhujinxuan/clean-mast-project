def get_height_display_name(height: float, marker: str = "") -> str:
    """Format height with interpolation marker for display.

    Returns e.g. "120m" or "120m(外推)". Parentheses indicate
    the value is an interpolated/extrapolated marker annotation.

    Args:
        height: Height in meters.
        marker: Annotation string (e.g. "外推", "内插", or "").

    Returns:
        Formatted display string.
    """
    base = f"{int(height)}m"
    if marker:
        return f"{base}({marker})"
    return base
