"""Pipeline phase entity.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-e-001-domain-entities
Compliance: Subdomain layout ✓ | Domain Entity ✓

Represents a single phase in the data processing pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class PhaseStatus(Enum):
    """Status of a pipeline phase."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


class PhaseType(Enum):
    """Type of pipeline phase."""

    RECOMMEND = auto()
    EXECUTE = auto()
    ANALYZE = auto()
    REPORT = auto()


@dataclass
class PipelinePhase:
    """A single phase in the processing pipeline.

    Attributes:
        name: Phase identifier (e.g., "recommend-fill-heights")
        phase_type: Type of phase (recommend, execute, analyze, report)
        status: Current execution status
        description: Human-readable description
        dependencies: List of phase names that must complete before this phase
        is_implemented: Whether this phase is implemented in Python
        config_file: Configuration file name pattern
    """

    name: str
    phase_type: PhaseType
    status: PhaseStatus = PhaseStatus.PENDING
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    is_implemented: bool = True
    config_file: str = ""

    def mark_running(self) -> None:
        """Mark phase as running."""
        self.status = PhaseStatus.RUNNING

    def mark_completed(self) -> None:
        """Mark phase as completed."""
        self.status = PhaseStatus.COMPLETED

    def mark_failed(self) -> None:
        """Mark phase as failed."""
        self.status = PhaseStatus.FAILED

    def mark_skipped(self) -> None:
        """Mark phase as skipped."""
        self.status = PhaseStatus.SKIPPED

    def can_run(self, completed_phases: set[str]) -> bool:
        """Check if phase can run given completed phases."""
        if self.status != PhaseStatus.PENDING:
            return False
        return all(dep in completed_phases for dep in self.dependencies)


# Phase definitions
IMPLEMENTED_PHASES = [
    "recommend-fill-heights",
    "execute-fill-heights",
    "recommend-wt-timeseries",
    "generate-wt-timeseries",
    "recommend-report",
    "generate-report",
]

UNIMPLEMENTED_PHASES = [
    "recommend-clean",
    "clean",
    "reconstruct-single",
    "train-meso",
    "reconstruct-meso",
]
