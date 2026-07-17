"""ProjectConfig — lazy discovery of all known TOML configs in a project directory."""

from pathlib import Path
from typing import ClassVar

from cleanmast.subdomains.configuration.model.discovered_config import DiscoveredConfig
from cleanmast.subdomains.configuration.model.fill_height_meso_config import (
    FillHeightsMesoConfiguration,
)
from cleanmast.subdomains.configuration.model.fill_height_rep_year_config import (
    FillHeightsRepYearConfiguration,
)
from cleanmast.subdomains.configuration.model.reconstruct_meso import (
    ReconstructMesoConfiguration,
)
from cleanmast.subdomains.configuration.model.report_config import FlatReportConfig
from cleanmast.subdomains.configuration.model.representative_year_config import (
    RepresentativeYearConfiguration,
)
from cleanmast.subdomains.configuration.model.wt_timeseries_config import (
    WtTimeSeriesConfiguration,
)
from cleanmast.subdomains.configuration.services.config_io import load_config


# ===========================================================================
# USAGE RESTRICTION: ProjectConfig is for RECOMMEND and ANALYZE commands ONLY.
#
# Registered consumers (Python):
#   recommend:  cleanmast recommend fill-heights
#               cleanmast recommend wt-timeseries
#               cleanmast recommend report-configs timeseries
#   analyze:    (none; analyse commands are Julia-side)
#
# EXECUTE COMMANDS MUST NOT call any discover_*_config() method.  They
# receive an explicit config_path from the CLI and MUST use:
#   from cleanmast.subdomains.configuration import load_config
#   config = load_config(ModelType, config_path)
#
# Reason: execute commands accept a specific config file as argument.
# Re-discovering by convention ignores the explicit path and creates
# unreachable branches when two configs of the same family coexist in one
# project (e.g. fill-heights-reconstruct-meso.toml and
# fill-heights-representative-year.toml).
# ===========================================================================
class ProjectConfig:
    """Lazy discovery of all known TOML configs in a project directory.

    Each ``discover_*`` method checks a private cache first, then looks for
    the corresponding TOML file on disk.  Missing files return ``None``;
    malformed files propagate the ``tomli.TOMLDecodeError`` or Pydantic
    ``ValidationError``.

    Usage::

        pc = ProjectConfig(Path("project_dir"))
        meso = pc.discover_reconstruct_meso_config()
        if meso is None:
            raise FileNotFoundError("reconstruct-meso.toml not found")
    """

    _FILENAMES: ClassVar[dict[type, str]] = {
        ReconstructMesoConfiguration: "reconstruct-meso.toml",
        RepresentativeYearConfiguration: "representative-year.toml",
        WtTimeSeriesConfiguration: "wt-timeseries.toml",
        FillHeightsMesoConfiguration: "fill-heights-reconstruct-meso.toml",
        FillHeightsRepYearConfiguration: "fill-heights-representative-year.toml",
        FlatReportConfig: "rep-ts-report.toml",
    }

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self._reconstruct_meso_config: DiscoveredConfig[ReconstructMesoConfiguration] | None = None
        self._representative_year_config: DiscoveredConfig[RepresentativeYearConfiguration] | None = None
        self._wt_timeseries_config: DiscoveredConfig[WtTimeSeriesConfiguration] | None = None
        self._fill_heights_meso_config: DiscoveredConfig[FillHeightsMesoConfiguration] | None = None
        self._fill_heights_rep_year_config: DiscoveredConfig[FillHeightsRepYearConfiguration] | None = None
        self._report_config: DiscoveredConfig[FlatReportConfig] | None = None

    def discover_reconstruct_meso_config(self) -> DiscoveredConfig[ReconstructMesoConfiguration] | None:
        """Discover and cache ``reconstruct-meso.toml``."""
        if self._reconstruct_meso_config is not None:
            return self._reconstruct_meso_config
        filename = self._FILENAMES[ReconstructMesoConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(ReconstructMesoConfiguration, path)
        self._reconstruct_meso_config = DiscoveredConfig(config=config, filename=filename)
        return self._reconstruct_meso_config

    def discover_representative_year_config(self) -> DiscoveredConfig[RepresentativeYearConfiguration] | None:
        """Discover and cache ``representative-year.toml``."""
        if self._representative_year_config is not None:
            return self._representative_year_config
        filename = self._FILENAMES[RepresentativeYearConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(RepresentativeYearConfiguration, path)
        self._representative_year_config = DiscoveredConfig(config=config, filename=filename)
        return self._representative_year_config

    def discover_wt_timeseries_config(self) -> DiscoveredConfig[WtTimeSeriesConfiguration] | None:
        """Discover and cache ``wt-timeseries.toml``."""
        if self._wt_timeseries_config is not None:
            return self._wt_timeseries_config
        filename = self._FILENAMES[WtTimeSeriesConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(WtTimeSeriesConfiguration, path)
        self._wt_timeseries_config = DiscoveredConfig(config=config, filename=filename)
        return self._wt_timeseries_config

    def discover_fill_heights_meso_config(self) -> DiscoveredConfig[FillHeightsMesoConfiguration] | None:
        """Discover and cache ``fill-heights-reconstruct-meso.toml``."""
        if self._fill_heights_meso_config is not None:
            return self._fill_heights_meso_config
        filename = self._FILENAMES[FillHeightsMesoConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(FillHeightsMesoConfiguration, path)
        self._fill_heights_meso_config = DiscoveredConfig(config=config, filename=filename)
        return self._fill_heights_meso_config

    def discover_fill_heights_rep_year_config(self) -> DiscoveredConfig[FillHeightsRepYearConfiguration] | None:
        """Discover and cache ``fill-heights-representative-year.toml``."""
        if self._fill_heights_rep_year_config is not None:
            return self._fill_heights_rep_year_config
        filename = self._FILENAMES[FillHeightsRepYearConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(FillHeightsRepYearConfiguration, path)
        self._fill_heights_rep_year_config = DiscoveredConfig(config=config, filename=filename)
        return self._fill_heights_rep_year_config

    def discover_report_config(self) -> DiscoveredConfig[FlatReportConfig] | None:
        """Discover and cache ``rep-ts-report.toml``."""
        if self._report_config is not None:
            return self._report_config
        filename = self._FILENAMES[FlatReportConfig]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(FlatReportConfig, path)
        self._report_config = DiscoveredConfig(config=config, filename=filename)
        return self._report_config
