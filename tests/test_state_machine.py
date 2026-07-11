import json
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.events import EventLogStore
from safeloop.llm.base import LLMRequest
from safeloop.llm.mock import MockLLMClient
from safeloop.run_manager import RunManager
from safeloop.state_machine import AgentStateMachine


def make_config(
    workspace: Path,
    max_steps: int = 10,
    test_command: str | None = None,
    redaction_secret_env_vars: list[str] | None = None,
) -> HarnessConfig:
    return HarnessConfig(
        workspace=workspace,
        test_command=test_command or "python -c \"print('tests pass')\"",
        blocked_commands=["git push"],
        approval_required_commands=["pip install"],
        max_steps=max_steps,
        redaction_secret_env_vars=redaction_secret_env_vars or ["DEEPSEEK_API_KEY"],
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
    assert {schema["name"] for schema in client.requests[0].tool_schemas} >= {"run_tests", "finish"}


def test_state_machine_redacts_configured_runtime_secret_from_feedback(tmp_path: Path, monkeypatch):
    env_var = "SAFELOOP_FEEDBACK_SECRET"
    known_secret = "alpha-token-123"
    monkeypatch.setenv(env_var, known_secret)
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = FeedbackAwareLLM()
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)
    config = make_config(
        tmp_path,
        test_command=(
            "python -c \"import sys; "
            "print('FAILED test_secret.py::test_x - alpha-token-123'); "
            "sys.exit(1)\""
        ),
        redaction_secret_env_vars=[env_var],
    )

    run = machine.run("protect feedback secrets", config)

    assert run.status == "finished"
    feedback = client.requests[1].feedback[0]
    assert known_secret not in feedback.summary
    assert known_secret not in feedback.raw_excerpt
    assert "[REDACTED]" in feedback.raw_excerpt


def test_state_machine_seeds_injected_event_store_with_runtime_secrets(tmp_path: Path, monkeypatch):
    env_var = "SAFELOOP_EVENT_SECRET"
    known_secret = "alpha-token-123"
    monkeypatch.setenv(env_var, known_secret)
    manager_store = EventLogStore()
    state_store = EventLogStore()
    manager = RunManager(event_store=manager_store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_command","arguments":{"command":"python -c \\"print(\\\'alpha-token-123\\\')\\""},"reason":"emit secret","expected_outcome":"fail"}',
            '{"tool_name":"finish","arguments":{"message":"done"},"reason":"stop","expected_outcome":"stop"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=state_store, llm_client=client)

    run = machine.run("protect split event stores", make_config(tmp_path, redaction_secret_env_vars=[env_var]))

    assert run.status == "finished"
    state_events_text = json.dumps([event.model_dump(mode="json") for event in state_store.list(run.id)])
    assert known_secret not in state_events_text
    assert "[REDACTED]" in state_events_text


class CapturingFinishLLM:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> str:
        self.requests.append(request)
        return '{"tool_name":"finish","arguments":{"message":"done"},"reason":"complete","expected_outcome":"stop"}'


def test_state_machine_does_not_send_configured_runtime_secret_from_memory_to_llm(tmp_path: Path, monkeypatch):
    env_var = "SAFELOOP_MEMORY_SECRET"
    known_secret = "alpha-token-123"
    monkeypatch.setenv(env_var, known_secret)
    memory_path = tmp_path / ".safeloop" / "memory.json"
    memory_path.parent.mkdir(parents=True)
    memory_path.write_text(
        json.dumps(
            [
                {
                    "id": "legacy-entry",
                    "scope": "project",
                    "tags": ["key"],
                    "content": f"token={known_secret}",
                }
            ]
        ),
        encoding="utf-8",
    )
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = CapturingFinishLLM()
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("protect secrets", make_config(tmp_path, redaction_secret_env_vars=[env_var]))

    assert run.status == "finished"
    assert known_secret not in client.requests[0].memories[0].content
    assert client.requests[0].memories[0].content == "token=[REDACTED]"


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


def test_state_machine_marks_failed_for_corrupt_memory_store(tmp_path: Path):
    memory_path = tmp_path / ".safeloop" / "memory.json"
    memory_path.parent.mkdir(parents=True)
    memory_path.write_text("{not-json", encoding="utf-8")
    store = EventLogStore()
    manager = RunManager(event_store=store)
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=MockLLMClient(responses=[]))

    run = machine.run("recover from bad memory", make_config(tmp_path))

    assert run.status == "failed"
    failed_event = next(event for event in store.list(run.id) if event.type == "failed")
    assert failed_event.payload["reason"] == "boundary_error"
    assert "not-json" not in str(failed_event.payload)


def test_state_machine_marks_failed_when_mock_llm_is_exhausted(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=MockLLMClient(responses=[]))

    run = machine.run("recover from llm failure", make_config(tmp_path))

    assert run.status == "failed"
    assert any(event.type == "failed" and event.payload["reason"] == "boundary_error" for event in store.list(run.id))
