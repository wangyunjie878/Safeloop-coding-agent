from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction
from safeloop.security.guardrails import GuardrailEngine, is_path_within_workspace


def make_config(workspace: Path) -> HarnessConfig:
    return HarnessConfig(
        workspace=workspace,
        test_command="python -m pytest",
        allowed_paths=["."],
        blocked_commands=["echo blocked"],
        approval_required_commands=["pip install"],
    )


def test_path_outside_workspace_is_blocked(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "app.py"
    inside.write_text("print('hello')", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    assert is_path_within_workspace(workspace, inside) is True
    assert is_path_within_workspace(workspace, outside) is False


def test_guardrail_denies_env_file(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": ".env"},
        reason="inspect",
        expected_outcome="content",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert decision.risk_level in {"high", "critical"}


def test_guardrail_denies_dangerous_command(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="run_command",
        arguments={"command": "rm -rf /"},
        reason="clean",
        expected_outcome="cleaned",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert "blocked" in decision.matched_rule


def test_guardrail_requires_approval_for_configured_command(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="run_command",
        arguments={"command": "pip install requests"},
        reason="install dependency",
        expected_outcome="installed",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "require_approval"
    assert decision.risk_level == "medium"


def test_guardrail_denies_over_approval_rule_when_both_match(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="run_command",
        arguments={"command": "pip install && git push"},
        reason="install dependency",
        expected_outcome="installed",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert decision.risk_level == "critical"


def test_guardrail_allows_safe_read_inside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")
    engine = GuardrailEngine(make_config(workspace))
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": "notes.txt"},
        reason="read notes",
        expected_outcome="content",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "allow"
    assert decision.risk_level == "low"


def test_guardrail_denies_unknown_action_with_sensitive_path(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="inspect_environment",
        arguments={"path": ".env"},
        reason="check config",
        expected_outcome="content",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert decision.risk_level in {"high", "critical"}


def test_guardrail_requires_approval_for_unknown_action_command(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="inspect_environment",
        arguments={"command": "pip install requests"},
        reason="install dependency",
        expected_outcome="installed",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "require_approval"
    assert decision.risk_level == "medium"
