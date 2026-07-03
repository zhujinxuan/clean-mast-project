"""FillHeights configuration subtype for representative-year context."""

from cleanmast.subdomains.configuration.model.fill_height_config import (
    FillHeightsConfiguration,
)


class FillHeightsRepYearConfiguration(FillHeightsConfiguration):
    """FillHeights configuration sourced from fill-heights-representative-year.toml.

    Marker subtype with identical schema — only the filename differs from
    FillHeightsMesoConfiguration.
    """

    pass
