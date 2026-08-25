"""Test JSON output structure for the cleanmast-dev verify command.

Expected JSON structure:
{
    "package": "cleanmast",
    "timestamp": "2026-04-08T...",
    "datasets": [
        {
            "name": str,
            "status": str,
            "duration_sec": float/int,
            "pull_status": str,
            "pull_duration_sec": float/int,
            "outputs": list,
            "error": str or None,
        }
    ],
    "summary": {"passed": int, "failed": int},
}
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from cleanmast_dev_tools.verify import verify
from click.testing import CliRunner, Result

JUSTFILE_CONTENT = "# mock justfile - content irrelevant, execution is mocked\n"


def _make_dataset(test_data: Path, package: str, name: str) -> Path:
    """Create test-data/{package}/{name}/Justfile and return the dataset dir."""
    ds_dir = test_data / package / name
    ds_dir.mkdir(parents=True)
    (ds_dir / "Justfile").write_text(JUSTFILE_CONTENT, encoding="utf-8")
    return ds_dir


def _pass_result(name: str) -> dict:
    return {
        "name": name,
        "status": "pass",
        "duration_sec": 1.0,
        "pull_status": "success",
        "pull_duration_sec": 0.5,
        "outputs": ["output.csv"],
        "error": None,
    }


def _fail_result(name: str) -> dict:
    return {
        "name": name,
        "status": "fail",
        "duration_sec": 1.0,
        "pull_status": "failed",
        "pull_duration_sec": 0.0,
        "outputs": [],
        "error": "just verify-json failed: boom",
    }


def _run(
    runner: CliRunner,
    test_data: Path,
    args: list[str],
    run_just_verify: MagicMock,
) -> Result:
    """Invoke verify with discovery/just-availability patched."""
    with patch(
        "cleanmast_dev_tools.verify._find_test_data_root"
    ) as mock_find_root, patch(
        "cleanmast_dev_tools.verify._can_use_just"
    ) as mock_can_use_just, patch(
        "cleanmast_dev_tools.verify._run_just_verify", run_just_verify
    ):
        mock_find_root.return_value = test_data
        mock_can_use_just.return_value = True
        return runner.invoke(verify, args)


class TestVerifyJsonStructure:
    """Tests for verify command JSON output structure."""

    def test_verify_json_structure(self, tmp_path: Path) -> None:
        """Test that verify --json produces the expected JSON structure."""
        runner = CliRunner()
        test_data = tmp_path / "test-data"
        test_data.mkdir()
        _make_dataset(test_data, "cleanmast", "test-dataset")

        run_just = MagicMock(return_value=(True, _pass_result("test-dataset"), 1.0))
        result = _run(runner, test_data, ["--json"], run_just)

        assert result.exit_code == 0, f"Command failed with: {result.output}"

        json_output = json.loads(result.output)

        # === Validate top-level structure ===
        assert "package" in json_output, "Missing 'package' field"
        assert "timestamp" in json_output, "Missing 'timestamp' field"
        assert "datasets" in json_output, "Missing 'datasets' field"
        assert "summary" in json_output, "Missing 'summary' field"

        # === Validate field types ===
        assert isinstance(json_output["package"], str), "'package' must be a string"
        assert isinstance(json_output["timestamp"], str), "'timestamp' must be a string"
        assert isinstance(json_output["datasets"], list), "'datasets' must be a list"
        assert isinstance(json_output["summary"], dict), "'summary' must be a dict"

        # === Validate datasets structure ===
        for dataset in json_output["datasets"]:
            # Required fields
            assert "name" in dataset, "Dataset missing 'name' field"
            assert "status" in dataset, "Dataset missing 'status' field"
            assert "duration_sec" in dataset, "Dataset missing 'duration_sec' field"
            assert "pull_status" in dataset, "Dataset missing 'pull_status' field"
            assert "pull_duration_sec" in dataset, "Dataset missing 'pull_duration_sec' field"
            assert "outputs" in dataset, "Dataset missing 'outputs' field"
            assert "error" in dataset, "Dataset missing 'error' field"

            # Field types
            assert isinstance(dataset["name"], str), "'name' must be a string"
            assert isinstance(dataset["status"], str), "'status' must be a string"
            assert isinstance(dataset["duration_sec"], (int, float))
            assert isinstance(dataset["pull_status"], str), "'pull_status' must be a string"
            assert isinstance(dataset["pull_duration_sec"], (int, float))
            assert isinstance(dataset["outputs"], list), "'outputs' must be a list"
            assert dataset["error"] is None or isinstance(dataset["error"], str)

        # === Validate summary structure ===
        assert "passed" in json_output["summary"], "Summary missing 'passed' field"
        assert "failed" in json_output["summary"], "Summary missing 'failed' field"
        assert isinstance(json_output["summary"]["passed"], int), "'passed' must be an int"
        assert isinstance(json_output["summary"]["failed"], int), "'failed' must be an int"

    def test_verify_json_with_package_filter(self, tmp_path: Path) -> None:
        """-p cleanmast returns its datasets and excludes other packages."""
        runner = CliRunner()
        test_data = tmp_path / "test-data"
        test_data.mkdir()
        _make_dataset(test_data, "cleanmast", "test-dataset")
        _make_dataset(test_data, "other-pkg", "other-dataset")

        def _side_effect(justfile_dir: Path, timeout: float = 1800.0):
            return (True, _pass_result(justfile_dir.name), 1.0)

        run_just = MagicMock(side_effect=_side_effect)
        result = _run(runner, test_data, ["--json", "--package", "cleanmast"], run_just)

        assert result.exit_code == 0, f"Command failed with: {result.output}"

        json_output = json.loads(result.output)

        # Should only have datasets from the cleanmast package
        assert len(json_output["datasets"]) == 1
        assert json_output["datasets"][0]["name"] == "test-dataset"
        # The excluded package's dataset was never executed
        assert run_just.call_count == 1
        assert run_just.call_args[0][0].name == "test-dataset"

    def test_verify_json_with_failing_dataset(self, tmp_path: Path) -> None:
        """A failing dataset reports summary.failed == 1 with the error propagated.

        --json mode still exits 0 - failures are reported in the JSON summary.
        """
        runner = CliRunner()
        test_data = tmp_path / "test-data"
        test_data.mkdir()
        _make_dataset(test_data, "cleanmast", "pass-dataset")
        _make_dataset(test_data, "cleanmast", "fail-dataset")

        def _side_effect(justfile_dir: Path, timeout: float = 1800.0):
            if justfile_dir.name == "fail-dataset":
                return (False, _fail_result("fail-dataset"), 1.0)
            return (True, _pass_result("pass-dataset"), 1.0)

        run_just = MagicMock(side_effect=_side_effect)
        result = _run(runner, test_data, ["--json"], run_just)

        assert result.exit_code == 0  # JSON output doesn't cause exit code 1

        json_output = json.loads(result.output)

        assert json_output["summary"]["passed"] == 1
        assert json_output["summary"]["failed"] == 1

        fail_dataset = next(
            (d for d in json_output["datasets"] if d["name"] == "fail-dataset"),
            None,
        )
        assert fail_dataset is not None
        assert fail_dataset["status"] == "fail"
        assert fail_dataset["error"] == "just verify-json failed: boom"

    def test_verify_dry_run_lists_datasets_without_running(self, tmp_path: Path) -> None:
        """--dry-run lists datasets with status 'dry-run' and runs nothing."""
        runner = CliRunner()
        test_data = tmp_path / "test-data"
        test_data.mkdir()
        _make_dataset(test_data, "cleanmast", "test-dataset")

        run_just = MagicMock(return_value=(True, _pass_result("test-dataset"), 1.0))
        result = _run(runner, test_data, ["--json", "--dry-run"], run_just)

        assert result.exit_code == 0, f"Command failed with: {result.output}"
        run_just.assert_not_called()

        json_output = json.loads(result.output)
        assert len(json_output["datasets"]) == 1
        assert json_output["datasets"][0]["name"] == "test-dataset"
        assert json_output["datasets"][0]["status"] == "dry-run"
        assert json_output["summary"]["passed"] == 0
        assert json_output["summary"]["failed"] == 0

    def test_verify_non_json_failure_exits_one(self, tmp_path: Path) -> None:
        """Non-json, non-dry-run failures exit 1 (the load-bearing quirk)."""
        runner = CliRunner()
        test_data = tmp_path / "test-data"
        test_data.mkdir()
        _make_dataset(test_data, "cleanmast", "fail-dataset")

        run_just = MagicMock(return_value=(False, _fail_result("fail-dataset"), 1.0))
        result = _run(runner, test_data, [], run_just)

        assert result.exit_code == 1
