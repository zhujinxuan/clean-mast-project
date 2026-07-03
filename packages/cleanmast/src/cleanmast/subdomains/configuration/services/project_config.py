"""ProjectConfig — lazy discovery of all known TOML configs in a project directory."""

from pathlib import Path
from typing import ClassVar

import tomli

from cleanmast.infrastructure.path_utils import to_posix_path
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
        with open(path, "rb") as f:
            data = tomli.load(f)
        config = ReconstructMesoConfiguration(**data)
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
        with open(path, "rb") as f:
            data = tomli.load(f)
        config = RepresentativeYearConfiguration(**data)
        self._representative_year_config = DiscoveredConfig(config=config, filename=filename)
        return self._representative_year_config

    def discover_wt_timeseries_config(self) -> DiscoveredConfig[WtTimeSeriesConfiguration] | None:
        """Discover and cache ``wt-timeseries.toml`` with path resolution."""
        if self._wt_timeseries_config is not None:
            return self._wt_timeseries_config
        filename = self._FILENAMES[WtTimeSeriesConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        with open(path, "rb") as f:
            data = tomli.load(f)

        # Resolve input paths to absolute (replicates old load_wt_timeseries_config logic)
        for mast_data in data.get("masts", []):
            if "input" in mast_data and "data" in mast_data["input"]:
                input_path = Path(mast_data["input"]["data"])
                if not input_path.is_absolute():
                    mast_data["input"]["data"] = to_posix_path(self.project_dir / input_path)

        config = WtTimeSeriesConfiguration(**data)
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
        with open(path, "rb") as f:
            data = tomli.load(f)
        config = FillHeightsMesoConfiguration(**data)
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
        with open(path, "rb") as f:
            data = tomli.load(f)
        config = FillHeightsRepYearConfiguration(**data)
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
        with open(path, "rb") as f:
            data = tomli.load(f)
        config = FlatReportConfig(**data)
        self._report_config = DiscoveredConfig(config=config, filename=filename)
        return self._report_config
