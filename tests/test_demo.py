import subprocess
import sys
from pathlib import Path
import shutil

from safeloop.demo import DEMO_RESPONSES, run_harness
from safeloop.demo import print_run_summary
from safeloop.models import Event, RunRecord


def _event_payloads(events, event_type: str):
    return [event.payload for event in events if event.type == event_type]

def test_demo_command_exits_zero_and_prints_mechanism_events():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "demo"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "guardrail_blocked" in result.stdout
    assert "feedback_added" in result.stdout
    assert "patch_file success=True" in result.stdout
    assert "run_tests success=True" in result.stdout
    assert "finished" in result.stdout


def test_print_run_summary_shows_failed_boundary_error(capsys):
    run = RunRecord(
        id="run-failed",
        task="write code",
        workspace=Path("."),
        status="failed",
        current_step=1,
    )
    events = [
        Event(
            run_id="run-failed",
            step=1,
            type="failed",
            payload={"reason": "boundary_error", "error": "DeepSeekClientError: request failed"},
        )
    ]

    print_run_summary(run, events)

    output = capsys.readouterr().out
    assert "boundary_error" in output
    assert "DeepSeekClientError: request failed" in output


def test_run_command_accepts_config_task_and_mock_finish_response(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {tmp_path}\n"
        "test_command: python -c \"print('ok')\"\n"
        "llm_provider: mock\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safeloop",
            "run",
            "--config",
            str(config_path),
            "--task",
            "verify",
            "--mock-response",
            '{"tool_name":"finish","arguments":{"message":"done"},"reason":"done","expected_outcome":"stop"}',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "finished" in result.stdout


def test_run_command_uses_default_mock_finish_response(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {tmp_path}\n"
        "test_command: python -c \"print('ok')\"\n"
        "llm_provider: mock\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safeloop",
            "run",
            "--config",
            str(config_path),
            "--task",
            "verify",
            "--llm",
            "mock",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "finished" in result.stdout


def test_demo_script_patches_bug_after_test_failure_feedback(tmp_path: Path):
    source = Path("samples/python_buggy_calculator")
    workspace = tmp_path / "python_buggy_calculator"
    shutil.copytree(source, workspace)
    config_path = workspace / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -c \"import calculator; assert calculator.subtract(4, 2) == 2\"\n"
        "llm_provider: mock\n"
        "allowed_paths:\n"
        "  - .\n"
        "max_steps: 8\n",
        encoding="utf-8",
    )

    run, events = run_harness("fix calculator", config_path, DEMO_RESPONSES)

    tool_results = _event_payloads(events, "tool_result")
    assert run.status == "finished"
    assert any(payload["tool_name"] == "run_tests" and payload["success"] is False for payload in tool_results)
    assert any(payload["tool_name"] == "patch_file" and payload["success"] is True for payload in tool_results)
    assert any(payload["tool_name"] == "run_tests" and payload["success"] is True for payload in tool_results)
