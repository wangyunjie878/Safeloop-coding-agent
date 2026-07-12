from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from safeloop.config import load_config
from safeloop.events import EventLogStore
from safeloop.llm.base import LLMClient
from safeloop.llm.mock import MockLLMClient
from safeloop.models import Event, RunRecord
from safeloop.run_manager import RunManager
from safeloop.state_machine import AgentStateMachine


_DANGEROUS_COMMAND_RESPONSE = (
    '{"tool_name":"run_command","arguments":{"command":"rm -rf /"},'
    '"reason":"show dangerous command blocking","expected_outcome":"guardrail denial"}'
)
_RUN_TESTS_RESPONSE = (
    '{"tool_name":"run_tests","arguments":{},'
    '"reason":"verify the sample calculator","expected_outcome":"test failure feedback"}'
)
_PATCH_RESPONSE = (
    '{"tool_name":"patch_file","arguments":{"path":"calculator.py",'
    '"old":"return left + right  # BUG: subtraction should subtract.",'
    '"new":"return left - right"},'
    '"reason":"fix subtraction after reading feedback","expected_outcome":"tests can pass"}'
)
_RUN_TESTS_AGAIN_RESPONSE = (
    '{"tool_name":"run_tests","arguments":{},'
    '"reason":"verify the patch","expected_outcome":"tests pass"}'
)
_FINISH_RESPONSE = (
    '{"tool_name":"finish","arguments":{"message":"sample calculator fixed"},'
    '"reason":"tests pass","expected_outcome":"stop"}'
)

DEMO_RESPONSES = [
    _DANGEROUS_COMMAND_RESPONSE,
    _RUN_TESTS_RESPONSE,
    _PATCH_RESPONSE,
    _RUN_TESTS_AGAIN_RESPONSE,
    _FINISH_RESPONSE,
]


def _sample_source() -> Path:
    return Path(__file__).resolve().parent.parent / "samples" / "python_buggy_calculator"


def run_harness_with_client(task: str, config_path: Path | str, llm_client: LLMClient) -> tuple[RunRecord, list[Event]]:
    config = load_config(config_path)
    store = EventLogStore()
    manager = RunManager(event_store=store)
    machine = AgentStateMachine(
        run_manager=manager,
        event_store=store,
        llm_client=llm_client,
    )

    run = machine.run(task, config)
    return run, store.list(run.id)


def run_harness(task: str, config_path: Path | str, mock_responses: list[str]) -> tuple[RunRecord, list[Event]]:
    return run_harness_with_client(task, config_path, MockLLMClient(mock_responses))


def print_run_summary(run: RunRecord, events: list[Event]) -> None:
    print(f"run_id: {run.id}")
    print(f"final_status: {run.status}")
    print("events:")
    for event in events:
        detail = ""
        if event.type == "feedback_added":
            detail = f" {event.payload.get('kind', '')}"
        elif event.type == "guardrail_decision":
            detail = f" {event.payload.get('decision', '')}"
        elif event.type == "tool_result":
            detail = f" {event.payload.get('tool_name', '')} success={event.payload.get('success', '')}"
        elif event.type == "finished":
            detail = f" {event.payload.get('message', '')}"
        print(f"- step={event.step} type={event.type}{detail}")


def run_demo() -> int:
    sample_source = _sample_source()
    with tempfile.TemporaryDirectory(prefix="safeloop-demo-") as temp_dir:
        workspace = Path(temp_dir) / "python_buggy_calculator"
        shutil.copytree(sample_source, workspace)
        config_path = workspace / "safeloop.yml"
        config_path.write_text(
            f"workspace: {workspace}\n"
            'test_command: python -c "import calculator; assert calculator.subtract(4, 2) == 2"\n'
            "llm_provider: mock\n"
            "allowed_paths:\n"
            "  - .\n"
            "blocked_commands:\n"
            "  - git push\n"
            "command_timeout_seconds: 10\n"
            "max_steps: 8\n",
            encoding="utf-8",
        )

        run, events = run_harness(
            "Fix the buggy calculator using the feedback loop.",
            config_path,
            DEMO_RESPONSES,
        )
        print_run_summary(run, events)
        return 0 if run.status == "finished" else 1
