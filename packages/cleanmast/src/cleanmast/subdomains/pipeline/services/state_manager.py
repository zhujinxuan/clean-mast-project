"""State manager service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓

Manages persistent state for pipeline execution.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PhaseState:
    """State of a single phase execution.

    Attributes:
        name: Phase name
        status: Execution status (pending, running, completed, failed, skipped)
        start_time: Execution start timestamp (ISO format)
        end_time: Execution end timestamp (ISO format)
        error_message: Error message if failed
        outputs: List of output files generated
    """

    name: str
    status: str = "pending"
    start_time: str = ""
    end_time: str = ""
    error_message: str = ""
    outputs: list[str] = field(default_factory=list)


class StateManager:
    """Manages pipeline execution state persistence.

    Saves and loads pipeline state to/from JSON file in project directory.
    """

    STATE_FILE = ".cleanmast_state.json"

    def __init__(self, project_dir: Path):
        """Initialize state manager.

        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.state_file = project_dir / self.STATE_FILE
        self._state: dict[str, PhaseState] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            self._state = {}
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._state = {
                name: PhaseState(**state_data)
                for name, state_data in data.get("phases", {}).items()
            }
        except (json.JSONDecodeError, TypeError):
            self._state = {}

    def _save_state(self) -> None:
        """Save state to file."""
        data = {
            "phases": {
                name: asdict(state) for name, state in self._state.items()
            }
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_phase_state(self, phase_name: str) -> PhaseState:
        """Get state for a phase.

        Args:
            phase_name: Phase name

        Returns:
            Phase state (creates new if not exists)
        """
        if phase_name not in self._state:
            self._state[phase_name] = PhaseState(name=phase_name)
        return self._state[phase_name]

    def update_phase_state(self, phase_name: str, **kwargs: Any) -> None:
        """Update phase state.

        Args:
            phase_name: Phase name
            **kwargs: State attributes to update
        """
        state = self.get_phase_state(phase_name)

        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        self._save_state()

    def mark_phase_started(self, phase_name: str, start_time: str) -> None:
        """Mark phase as started.

        Args:
            phase_name: Phase name
            start_time: Start timestamp (ISO format)
        """
        self.update_phase_state(
            phase_name,
            status="running",
            start_time=start_time,
        )

    def mark_phase_completed(self, phase_name: str, end_time: str, outputs: list[str]) -> None:
        """Mark phase as completed.

        Args:
            phase_name: Phase name
            end_time: End timestamp (ISO format)
            outputs: List of output files
        """
        self.update_phase_state(
            phase_name,
            status="completed",
            end_time=end_time,
            outputs=outputs,
        )

    def mark_phase_failed(self, phase_name: str, end_time: str, error_message: str) -> None:
        """Mark phase as failed.

        Args:
            phase_name: Phase name
            end_time: End timestamp (ISO format)
            error_message: Error message
        """
        self.update_phase_state(
            phase_name,
            status="failed",
            end_time=end_time,
            error_message=error_message,
        )

    def mark_phase_skipped(self, phase_name: str) -> None:
        """Mark phase as skipped.

        Args:
            phase_name: Phase name
        """
        self.update_phase_state(phase_name, status="skipped")

    def get_completed_phases(self) -> list[str]:
        """Get list of completed phase names."""
        return [
            name for name, state in self._state.items()
            if state.status == "completed"
        ]

    def get_failed_phases(self) -> list[str]:
        """Get list of failed phase names."""
        return [
            name for name, state in self._state.items()
            if state.status == "failed"
        ]

    def is_phase_completed(self, phase_name: str) -> bool:
        """Check if phase is completed.

        Args:
            phase_name: Phase name

        Returns:
            True if completed, False otherwise
        """
        state = self.get_phase_state(phase_name)
        return state.status == "completed"

    def reset_state(self) -> None:
        """Reset all state."""
        self._state = {}
        if self.state_file.exists():
            self.state_file.unlink()

    def get_all_state(self) -> dict[str, PhaseState]:
        """Get all phase states."""
        return dict(self._state)
