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


def test_run_record_matches_documented_contract():
    fields = list(RunRecord.model_fields)

    assert fields == [
        "id",
        "task",
        "workspace",
        "status",
        "current_step",
        "max_steps",
        "created_at",
        "finished_at",
    ]
    assert set(RunRecord.model_fields["status"].annotation.__args__) == {
        "created",
        "running",
        "waiting_approval",
        "finished",
        "stopped",
        "failed",
    }


def test_agent_action_captures_requested_action():
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": "app.py"},
        reason="inspect target file",
        expected_outcome="source content",
    )

    assert action.tool_name == "read_file"
    assert action.arguments["path"] == "app.py"


def test_tool_result_matches_documented_contract():
    fields = list(ToolResult.model_fields)

    assert fields == [
        "tool_name",
        "success",
        "exit_code",
        "stdout",
        "stderr",
        "summary",
        "duration_ms",
    ]


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


def test_guardrail_decision_matches_documented_contract():
    fields = list(GuardrailDecision.model_fields)

    assert fields == ["decision", "risk_level", "reason", "matched_rule"]
    assert set(GuardrailDecision.model_fields["decision"].annotation.__args__) == {
        "allow",
        "deny",
        "require_approval",
    }
    assert set(GuardrailDecision.model_fields["risk_level"].annotation.__args__) == {
        "low",
        "medium",
        "high",
        "critical",
    }


def test_guardrail_decision_uses_known_values():
    decision = GuardrailDecision(
        decision="deny",
        risk_level="critical",
        reason="dangerous command",
        matched_rule="blocked_commands",
    )

    assert decision.decision == "deny"


def test_feedback_matches_documented_contract():
    fields = list(Feedback.model_fields)

    assert fields == ["kind", "summary", "raw_excerpt", "suggested_next_context"]
    assert set(Feedback.model_fields["kind"].annotation.__args__) == {
        "test_failure",
        "syntax_error",
        "timeout",
        "guardrail_blocked",
        "tool_error",
        "parse_error",
        "generic_failure",
    }


def test_memory_entry_matches_documented_contract():
    fields = list(MemoryEntry.model_fields)

    assert fields == ["id", "scope", "tags", "content", "created_at", "source_run_id"]
    assert set(MemoryEntry.model_fields["scope"].annotation.__args__) == {
        "project",
        "run",
        "user",
    }


def test_event_can_wrap_a_named_payload():
    event = Event(
        run_id="run-1",
        step=1,
        type="state_changed",
        payload={"status": "created"},
    )

    assert event.type == "state_changed"
    assert event.payload["status"] == "created"


def test_other_core_models_exist():
    run = RunRecord(id="run-1", task="verify", workspace="/tmp/project", status="created")
    feedback = Feedback(kind="generic_failure", summary="keep going", raw_excerpt="", suggested_next_context="")
    memory = MemoryEntry(
        id="memory-1",
        scope="project",
        tags=["lesson"],
        content="resolve paths",
        created_at="2026-07-10T00:00:00Z",
    )
    config = HarnessConfig(workspace="/tmp/project", test_command="python -m pytest")

    assert run.id == "run-1"
    assert feedback.kind == "generic_failure"
    assert memory.tags == ["lesson"]
    assert config.max_steps == 10
