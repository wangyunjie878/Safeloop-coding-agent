from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.events import EventLogStore
from safeloop.llm.base import LLMRequest
from safeloop.llm.mock import MockLLMClient
from safeloop.run_manager import RunManager
from safeloop.state_machine import AgentStateMachine


def make_config(workspace: Path, max_steps: int = 10, test_command: str | None = None) -> HarnessConfig:
    return HarnessConfig(
        workspace=workspace,
        test_command=test_command or "python -c \"print('tests pass')\"",
        blocked_commands=["git push"],
        approval_required_commands=["pip install"],
        max_steps=max_steps,
    )


def event_types(store: EventLogStore, run_id: str) -> list[str]:
    return [event.type for event in store.list(run_id)]


def test_state_machine_finishes_with_mock_llm(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
            '{"tool_name":"finish","arguments":{"message":"done"},"reason":"tests pass","expected_outcome":"stop"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("verify project", make_config(tmp_path))

    assert run.status == "finished"
    assert "tool_result" in event_types(store, run.id)
    assert "finished" in event_types(store, run.id)


def test_state_machine_guardrail_blocks_dangerous_action_before_dispatch(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_command","arguments":{"command":"rm -rf /"},"reason":"clean","expected_outcome":"clean"}',
            '{"tool_name":"finish","arguments":{"message":"blocked safely"},"reason":"blocked","expected_outcome":"stop"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("avoid dangerous command", make_config(tmp_path))
    events = store.list(run.id)

    assert run.status == "finished"
    assert any(event.type == "guardrail_decision" and event.payload["decision"] == "deny" for event in events)
    assert any(event.type == "feedback_added" and event.payload["kind"] == "guardrail_blocked" for event in events)
    assert not any(event.type == "tool_result" and event.payload["tool_name"] == "run_command" for event in events)


class FeedbackAwareLLM:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> str:
        self.requests.append(request)
        if not request.feedback:
            return '{"tool_name":"run_tests","arguments":{},"reason":"first verify","expected_outcome":"fail"}'
        return '{"tool_name":"finish","arguments":{"message":"used feedback"},"reason":"saw feedback","expected_outcome":"stop"}'


def test_state_machine_feeds_test_failure_back_to_next_llm_request(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = FeedbackAwareLLM()
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)
    config = make_config(
        tmp_path,
        test_command='python -c "import sys; print(\'FAILED test_app.py::test_x - AssertionError\'); sys.exit(1)"',
    )

    run = machine.run("fix failing tests", config)

    assert run.status == "finished"
    assert len(client.requests) == 2
    assert client.requests[1].feedback[0].kind == "test_failure"


def test_state_machine_stops_after_two_parse_errors(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(responses=["not json", "still not json"])
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("parse robustly", make_config(tmp_path))

    assert run.status == "stopped"
    assert any(event.type == "stopped" and event.payload["reason"] == "parse_errors" for event in store.list(run.id))


def test_state_machine_stops_at_max_steps(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
            '{"tool_name":"run_tests","arguments":{},"reason":"verify again","expected_outcome":"pass"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("never finish", make_config(tmp_path, max_steps=2))

    assert run.status == "stopped"
    assert any(event.type == "stopped" and "max_steps" in event.payload["reason"] for event in store.list(run.id))
