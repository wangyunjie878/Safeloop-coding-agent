from safeloop.models import (
    AgentAction,
    Event,
    Feedback,
    GuardrailDecision,
    HarnessConfig,
    MemoryEntry,
    RunRecord,
    ToolResult,
)


def test_agent_action_captures_requested_action():
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": "app.py"},
        reason="inspect target file",
        expected_outcome="source content",
    )

    assert action.tool_name == "read_file"
    assert action.arguments["path"] == "app.py"


def test_tool_result_exposes_execution_summary():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="",
        stderr="E   AssertionError",
        summary="tests failed",
        duration_ms=12,
    )

    assert result.success is False
    assert result.exit_code == 1


def test_guardrail_decision_uses_known_values():
    decision = GuardrailDecision(
        decision="deny",
        risk_level="critical",
        reason="dangerous command",
        matched_rule="blocked_commands",
    )

    assert decision.decision == "deny"


def test_event_can_wrap_a_named_payload():
    event = Event(
        type="state_changed",
        run_id="run-1",
        payload={"status": "created"},
    )

    assert event.type == "state_changed"
    assert event.payload["status"] == "created"


def test_other_core_models_exist():
    run = RunRecord(run_id="run-1", task="verify", status="created")
    feedback = Feedback(source="user", message="keep going")
    memory = MemoryEntry(key="lesson", value="resolve paths")
    config = HarnessConfig(workspace="/tmp/project", test_command="python -m pytest")

    assert run.run_id == "run-1"
    assert feedback.source == "user"
    assert memory.key == "lesson"
    assert config.max_steps == 10
