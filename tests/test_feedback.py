from safeloop.feedback import FeedbackClassifier
from safeloop.models import GuardrailDecision, ToolResult


def test_classifier_detects_test_failure():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="FAILED test_app.py::test_add - AssertionError",
        stderr="",
        summary="tests failed",
        duration_ms=20,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert feedback.kind == "test_failure"
    assert "AssertionError" in feedback.raw_excerpt
    assert "test failure" in feedback.suggested_next_context.lower()


def test_classifier_detects_syntax_error_from_summary():
    result = ToolResult(
        tool_name="run_command",
        success=False,
        exit_code=1,
        stdout="",
        stderr="",
        summary="SyntaxError: invalid syntax",
        duration_ms=5,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert feedback.kind == "syntax_error"
    assert "SyntaxError" in feedback.summary


def test_classifier_detects_timeout_from_summary():
    result = ToolResult(
        tool_name="run_command",
        success=False,
        exit_code=None,
        stdout="",
        stderr="",
        summary="command timeout after 1 seconds",
        duration_ms=1000,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert feedback.kind == "timeout"
    assert "timeout" in feedback.summary.lower()


def test_classifier_detects_guardrail_blocked():
    decision = GuardrailDecision(
        decision="deny",
        risk_level="critical",
        reason="command matches blocked pattern",
        matched_rule="blocked_command:rm -rf /",
    )

    feedback = FeedbackClassifier().from_guardrail(decision)

    assert feedback.kind == "guardrail_blocked"
    assert "blocked" in feedback.summary.lower()
    assert "rm -rf /" in feedback.raw_excerpt


def test_classifier_detects_parse_error():
    feedback = FeedbackClassifier().from_parse_error("invalid JSON object")

    assert feedback.kind == "parse_error"
    assert "invalid JSON object" in feedback.summary
    assert "valid JSON" in feedback.suggested_next_context


def test_classifier_truncates_long_output():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="A" * 80,
        stderr="",
        summary="tests failed",
        duration_ms=20,
    )

    feedback = FeedbackClassifier(max_excerpt_chars=32).from_tool_result(result)

    assert len(feedback.raw_excerpt) == 32
    assert "truncated" in feedback.summary.lower()
    assert "truncated" in feedback.suggested_next_context.lower()


def test_classifier_redacts_secret_like_content():
    result = ToolResult(
        tool_name="run_command",
        success=False,
        exit_code=1,
        stdout="DEEPSEEK_API_KEY=sk-live-secret12345678\nFAILED test.py::test_secret",
        stderr="",
        summary="command failed with sk-live-secret12345678",
        duration_ms=20,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert "sk-live-secret12345678" not in feedback.summary
    assert "sk-live-secret12345678" not in feedback.raw_excerpt
    assert "DEEPSEEK_API_KEY" not in feedback.raw_excerpt
    assert "[REDACTED]" in feedback.summary
    assert "[REDACTED]" in feedback.raw_excerpt


def test_classifier_redacts_configured_known_secret_values():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="FAILED test_secret.py::test_x - alpha-token-123",
        stderr="",
        summary="tests failed with alpha-token-123",
        duration_ms=20,
    )

    feedback = FeedbackClassifier().from_tool_result(result, known_secrets=["alpha-token-123"])

    assert "alpha-token-123" not in feedback.summary
    assert "alpha-token-123" not in feedback.raw_excerpt
    assert "[REDACTED]" in feedback.summary
    assert "[REDACTED]" in feedback.raw_excerpt
