"""Pipeline orchestrator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓

Coordinates execution of pipeline phases in the correct order.
"""

from pathlib import Path

from cleanmast.subdomains.pipeline.entities.pipeline_phase import (
    PhaseStatus,
    PhaseType,
    PipelinePhase,
)


class PipelineOrchestrator:
    """Orchestrates the execution of processing pipeline phases.

    Manages phase dependencies and coordinates execution order.
    """

    def __init__(self, project_dir: Path):
        """Initialize orchestrator with project directory.

        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.phases: dict[str, PipelinePhase] = {}
        self._initialize_phases()

    def _initialize_phases(self) -> None:
        """Initialize all pipeline phases."""
        phase_configs = [
            # Implemented phases
            ("recommend-fill-heights", PhaseType.RECOMMEND, True, ["parse-sensors"]),
            ("execute-fill-heights", PhaseType.EXECUTE, True, ["recommend-fill-heights"]),
            ("recommend-wt-timeseries", PhaseType.RECOMMEND, True, ["execute-fill-heights"]),
            ("generate-wt-timeseries", PhaseType.EXECUTE, True, ["recommend-wt-timeseries"]),
            ("recommend-report", PhaseType.RECOMMEND, True, ["generate-wt-timeseries"]),
            ("generate-report", PhaseType.REPORT, True, ["recommend-report"]),

            # Unimplemented phases (use Julia)
            ("recommend-clean", PhaseType.RECOMMEND, False, ["parse-sensors"]),
            ("clean", PhaseType.EXECUTE, False, ["recommend-clean"]),
            ("reconstruct-single", PhaseType.EXECUTE, False, ["clean"]),
            ("train-meso", PhaseType.EXECUTE, False, ["clean"]),
            ("reconstruct-meso", PhaseType.EXECUTE, False, ["train-meso"]),
        ]

        for name, phase_type, is_implemented, deps in phase_configs:
            self.phases[name] = PipelinePhase(
                name=name,
                phase_type=phase_type,
                description=self._get_phase_description(name),
                dependencies=deps,
                is_implemented=is_implemented,
            )

    def _get_phase_description(self, phase_name: str) -> str:
        """Get human-readable description for phase."""
        descriptions = {
            "recommend-fill-heights": "Generate fill-heights configuration",
            "execute-fill-heights": "Execute fill-heights processing",
            "recommend-wt-timeseries": "Generate WT TimeSeries configuration",
            "generate-wt-timeseries": "Generate WT TimeSeries files",
            "recommend-report": "Generate report configuration",
            "generate-report": "Generate analysis report",
            "recommend-clean": "Generate data cleaning configuration",
            "clean": "Execute data cleaning",
            "reconstruct-single": "Execute single-mast reconstruction",
            "train-meso": "Train mesoscale correlation model",
            "reconstruct-meso": "Execute mesoscale reconstruction",
        }
        return descriptions.get(phase_name, phase_name)

    def get_implemented_phases(self) -> list[str]:
        """Get list of implemented phase names."""
        return [
            name for name, phase in self.phases.items()
            if phase.is_implemented
        ]

    def get_unimplemented_phases(self) -> list[str]:
        """Get list of unimplemented phase names."""
        return [
            name for name, phase in self.phases.items()
            if not phase.is_implemented
        ]

    def get_runnable_phases(self) -> list[PipelinePhase]:
        """Get phases that are ready to run."""
        completed = {
            name for name, phase in self.phases.items()
            if phase.status == PhaseStatus.COMPLETED
        }

        return [
            phase for phase in self.phases.values()
            if phase.can_run(completed)
        ]

    def execute_phase(self, phase_name: str) -> None:
        """Execute a single phase.

        Args:
            phase_name: Name of phase to execute

        Raises:
            ValueError: If phase doesn't exist
            NotImplementedError: If phase is not implemented in Python
            RuntimeError: If phase dependencies not met
        """
        if phase_name not in self.phases:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = self.phases[phase_name]

        if not phase.is_implemented:
            raise NotImplementedError(
                f"Phase '{phase_name}' is not implemented in Python. "
                f"Use: julia bin/CleanMast.jl {phase_name.replace('-', ' ')}"
            )

        completed = {
            name for name, p in self.phases.items()
            if p.status == PhaseStatus.COMPLETED
        }

        if not phase.can_run(completed):
            missing = set(phase.dependencies) - completed
            raise RuntimeError(
                f"Cannot run phase '{phase_name}'. "
                f"Missing dependencies: {missing}"
            )

        phase.mark_running()

        try:
            self._execute_phase_impl(phase)
            phase.mark_completed()
        except Exception as e:
            phase.mark_failed()
            raise RuntimeError(f"Phase '{phase_name}' failed: {e}") from e

    def _execute_phase_impl(self, phase: PipelinePhase) -> None:
        """Execute phase implementation.

        Args:
            phase: Phase to execute
        """
        from cleanmast.application.usecases.execute_fill_heights import (
            execute_fill_heights,
        )
        from cleanmast.application.usecases.generate_wt_timeseries import (
            generate_wt_timeseries,
        )
        from cleanmast.application.usecases.recommend_fill_heights import (
            recommend_fill_heights,
        )
        from cleanmast.application.usecases.recommend_wt_timeseries import (
            recommend_wt_timeseries,
        )

        executors = {
            "recommend-fill-heights": lambda: recommend_fill_heights(
                str(self.project_dir), "125,140,160", 1.125
            ),
            "execute-fill-heights": lambda: execute_fill_heights(
                str(self.project_dir / "fill-heights-reconstruct-meso.toml")
            ),
            "recommend-wt-timeseries": lambda: recommend_wt_timeseries(self.project_dir),
            "generate-wt-timeseries": lambda: generate_wt_timeseries(
                self.project_dir / "wt-timeseries.toml"
            ),
        }

        if phase.name in executors:
            executors[phase.name]()
        else:
            raise NotImplementedError(f"Execution not implemented for {phase.name}")

    def execute_pipeline(self, from_phase: str | None = None, to_phase: str | None = None) -> None:
        """Execute pipeline from one phase to another.

        Args:
            from_phase: Starting phase (inclusive). If None, starts from first runnable.
            to_phase: Ending phase (inclusive). If None, runs to completion.
        """
        phases_to_run = self._get_phase_range(from_phase, to_phase)

        for phase_name in phases_to_run:
            phase = self.phases[phase_name]

            if not phase.is_implemented:
                print(f"Skipping unimplemented phase: {phase_name}")
                continue

            print(f"Executing phase: {phase_name}")
            self.execute_phase(phase_name)
            print(f"Completed phase: {phase_name}")

    def _get_phase_range(self, from_phase: str | None, to_phase: str | None) -> list[str]:
        """Get ordered list of phases in range."""
        all_phases = list(self.phases.keys())

        if from_phase is None:
            start_idx = 0
        else:
            start_idx = all_phases.index(from_phase)

        if to_phase is None:
            end_idx = len(all_phases)
        else:
            end_idx = all_phases.index(to_phase) + 1

        return all_phases[start_idx:end_idx]

    def get_status(self) -> dict[str, str]:
        """Get status of all phases."""
        return {
            name: phase.status.name for name, phase in self.phases.items()
        }
