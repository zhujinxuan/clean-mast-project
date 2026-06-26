"""Height filter utilities for turbulence analysis."""


def select_interested_heights(
    heights: list[float],
    min_height: float = 120.0,
    max_height: float = 160.0,
    min_count: int = 2,
) -> list[float]:
    """Select heights within the target range, falling back to top heights.

    Returns all heights where ``min_height <= h <= max_height``, sorted
    ascending.  If fewer than ``min_count`` heights fall within the range,
    returns the ``min_count`` highest heights from the full set (or all heights
    if fewer than ``min_count`` total).

    Args:
        heights: List of sensor heights.
        min_height: Lower inclusive bound of the preferred height range.
        max_height: Upper inclusive bound of the preferred height range.
        min_count: Minimum number of heights to return.

    Returns:
        Sorted list of selected heights.
    """
    filtered = [h for h in heights if min_height <= h <= max_height]
    filtered.sort()

    if len(filtered) >= min_count:
        return filtered

    sorted_heights = sorted(heights, reverse=True)
    fallback = sorted_heights[:min_count]
    fallback.sort()
    return fallback
