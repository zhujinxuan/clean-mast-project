"""FillHeights configuration subtype for reconstruct-meso context."""

from cleanmast.subdomains.configuration.model.fill_height_config import (
    FillHeightsConfiguration,
)


class FillHeightsMesoConfiguration(FillHeightsConfiguration):
    """FillHeights configuration sourced from fill-heights-reconstruct-meso.toml.

    Marker subtype with identical schema — only the filename differs from
    FillHeightsRepYearConfiguration.
    """

    pass
