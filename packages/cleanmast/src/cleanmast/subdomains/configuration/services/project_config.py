"""ProjectConfig — lazy discovery of all known TOML configs in a project directory."""

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from cleanmast.subdomains.configuration.model.fill_height_fit_result import (
        FillHeightFitResult,
    )

from cleanmast.shared.timeseries.fill_height_meso_config import (
    FillHeightsMesoConfiguration,
)
from cleanmast.shared.timeseries.fill_height_rep_year_config import (
    FillHeightsRepYearConfiguration,
)
from cleanmast.shared.timeseries.wt_timeseries_config import (
    WtTimeSeriesConfiguration,
)
from cleanmast.subdomains.configuration.model.clean_config import (
    CleanRule,
    CleanRulesFile,
    ProcessCleanConfiguration,
)
from cleanmast.subdomains.configuration.model.discovered_config import DiscoveredConfig
from cleanmast.subdomains.configuration.model.reconstruct_meso import (
    ReconstructMesoConfiguration,
)
from cleanmast.subdomains.configuration.model.report_config import FlatReportConfig
from cleanmast.subdomains.configuration.model.representative_year_config import (
    RepresentativeYearConfiguration,
)
from cleanmast.subdomains.configuration.model.tower_shading_config import (
    TowerShadingConfiguration,
)
from cleanmast.subdomains.configuration.services.config_io import load_config, save_config


def load_clean_rules(
    rules_config: "str | list[CleanRule]",
    project_dir: Path,
) -> list[CleanRule]:
    """Resolve a mast's ``rules`` config into parsed rules (Julia ``load_rules``).

    Args:
        rules_config: Either a path to a rules preset file (relative paths
            resolve against ``project_dir``, mirroring Julia ``load_rules``)
            or an inline list of already-parsed rules.
        project_dir: Project directory used to resolve relative rule-file paths.

    Returns:
        The parsed rule list.

    Raises:
        FileNotFoundError: If a rule-file path does not exist under the project.
    """
    if isinstance(rules_config, str):
        path = Path(rules_config)
        if not path.is_absolute():
            path = project_dir / path
        return load_config(CleanRulesFile, path).rules
    return rules_config


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
        ProcessCleanConfiguration: "process-clean.toml",
        TowerShadingConfiguration: "tower-shading.toml",
    }

    _FILL_MODELS_SUBDIR: ClassVar[str] = "fill-models"

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self._reconstruct_meso_config: DiscoveredConfig[ReconstructMesoConfiguration] | None = None
        self._representative_year_config: DiscoveredConfig[RepresentativeYearConfiguration] | None = None
        self._wt_timeseries_config: DiscoveredConfig[WtTimeSeriesConfiguration] | None = None
        self._fill_heights_meso_config: DiscoveredConfig[FillHeightsMesoConfiguration] | None = None
        self._fill_heights_rep_year_config: DiscoveredConfig[FillHeightsRepYearConfiguration] | None = None
        self._report_config: DiscoveredConfig[FlatReportConfig] | None = None
        self._process_clean_config: DiscoveredConfig[ProcessCleanConfiguration] | None = None
        self._tower_shading_config: DiscoveredConfig[TowerShadingConfiguration] | None = None
        self._fill_height_models: dict[str, dict[str, DiscoveredConfig[FillHeightFitResult]]] | None = None

    def discover_process_clean_config(self) -> DiscoveredConfig[ProcessCleanConfiguration] | None:
        """Discover and cache ``process-clean.toml``."""
        if self._process_clean_config is not None:
            return self._process_clean_config
        filename = self._FILENAMES[ProcessCleanConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(ProcessCleanConfiguration, path)
        self._process_clean_config = DiscoveredConfig(config=config, filename=filename)
        return self._process_clean_config

    def discover_tower_shading_config(self) -> DiscoveredConfig[TowerShadingConfiguration] | None:
        """Discover and cache ``tower-shading.toml``."""
        if self._tower_shading_config is not None:
            return self._tower_shading_config
        filename = self._FILENAMES[TowerShadingConfiguration]
        path = self.project_dir / filename
        if not path.exists():
            return None
        config = load_config(TowerShadingConfiguration, path)
        self._tower_shading_config = DiscoveredConfig(config=config, filename=filename)
        return self._tower_shading_config

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

    def discover_fill_height_models(self) -> "dict[str, dict[str, DiscoveredConfig[FillHeightFitResult]]]":
        """Discover and cache trained fill-height models under ``fill-models/``.

        Walks ``fill-models/{mast}/{strategy}/*-fit.toml`` (two levels: mast,
        then strategy) and lazy-loads each file.  The inner key is
        ``"{strategy}/{variable}"``, e.g. ``"remove-top-layer/ws"``.

        Returns:
            ``{mast_name: {strategy_key: DiscoveredConfig}}``; empty dict when
            the ``fill-models/`` directory does not exist.
        """
        from cleanmast.subdomains.configuration.model.fill_height_fit_result import (
            FillHeightFitResult,
        )

        if self._fill_height_models is not None:
            return self._fill_height_models

        models: dict[str, dict[str, DiscoveredConfig[FillHeightFitResult]]] = {}
        root = self.project_dir / self._FILL_MODELS_SUBDIR
        if root.is_dir():
            for mast_dir in sorted(p for p in root.iterdir() if p.is_dir()):
                mast_models: dict[str, DiscoveredConfig[FillHeightFitResult]] = {}
                for strategy_dir in sorted(p for p in mast_dir.iterdir() if p.is_dir()):
                    for fit_file in sorted(strategy_dir.glob("*-fit.toml")):
                        variable = fit_file.stem.removesuffix("-fit")
                        config = load_config(FillHeightFitResult, fit_file)
                        key = f"{strategy_dir.name}/{variable}"
                        filename = fit_file.relative_to(self.project_dir).as_posix()
                        mast_models[key] = DiscoveredConfig(config=config, filename=filename)
                if mast_models:
                    models[mast_dir.name] = mast_models

        self._fill_height_models = models
        return models

    def save_fill_height_model(
        self,
        result: "FillHeightFitResult",
        mast_name: str,
        strategy: str,
        variable: str,
    ) -> Path:
        """Persist a trained fill-height model under ``fill-models/``.

        Writes to
        ``fill-models/{mast_name}/{strategy}/{variable}-fit.toml`` and updates
        the discovery cache.  This method is the single owner of the
        ``fill-models/`` directory layout — consumers never construct these
        paths themselves.

        Returns:
            The path the model was written to.
        """
        path = (
            self.project_dir
            / self._FILL_MODELS_SUBDIR
            / mast_name
            / strategy
            / f"{variable}-fit.toml"
        )
        save_config(result, path)

        if self._fill_height_models is not None:
            key = f"{strategy}/{variable}"
            filename = path.relative_to(self.project_dir).as_posix()
            self._fill_height_models.setdefault(mast_name, {})[key] = DiscoveredConfig(
                config=result, filename=filename
            )

        return path
