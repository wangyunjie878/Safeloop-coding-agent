from __future__ import annotations

from safeloop.models import Feedback, GuardrailDecision, ToolResult
from safeloop.security.redaction import redact_secrets


class FeedbackClassifier:
    def __init__(self, max_excerpt_chars: int = 1200):
        self._max_excerpt_chars = max_excerpt_chars

    def from_tool_result(self, result: ToolResult) -> Feedback:
        combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        source_text = combined_output or result.summary
        raw_excerpt, truncated = self._excerpt(source_text)
        summary = result.summary or "tool result"

        if "timeout" in result.summary.casefold():
            kind = "timeout"
            summary = summary or "tool timed out"
            next_context = "The previous tool call timed out. Try a smaller or safer next action."
        elif "syntaxerror" in result.summary.casefold():
            kind = "syntax_error"
            next_context = "The previous action produced a syntax error. Inspect the syntax before retrying."
        elif result.exit_code not in (None, 0) and self._looks_like_test_failure(combined_output):
            kind = "test_failure"
            next_context = "The previous result is a test failure. Use the failure excerpt to choose the next fix."
        elif not result.success:
            kind = "tool_error"
            next_context = "The previous tool call failed. Use the result summary and excerpt before retrying."
        else:
            kind = "generic_failure"
            next_context = "The previous result should be reviewed before choosing the next action."

        if truncated:
            summary = f"{summary} (raw output truncated)"
            next_context = f"{next_context} The raw excerpt was truncated."

        return Feedback(
            kind=kind,
            summary=self._redact_text(summary),
            raw_excerpt=raw_excerpt,
            suggested_next_context=self._redact_text(next_context),
        )

    def from_parse_error(self, message: str) -> Feedback:
        raw_excerpt, truncated = self._excerpt(message)
        summary = "parse error: invalid JSON action"
        if message:
            summary = f"parse error: {message}"
        next_context = "Return one valid JSON object with tool_name, arguments, reason, and expected_outcome."
        if truncated:
            summary = f"{summary} (raw output truncated)"
            next_context = f"{next_context} The raw excerpt was truncated."
        return Feedback(
            kind="parse_error",
            summary=self._redact_text(summary),
            raw_excerpt=raw_excerpt,
            suggested_next_context=self._redact_text(next_context),
        )

    def from_guardrail(self, decision: GuardrailDecision) -> Feedback:
        raw_text = "\n".join(part for part in (decision.reason, decision.matched_rule) if part)
        raw_excerpt, truncated = self._excerpt(raw_text)
        if decision.decision == "deny":
            kind = "guardrail_blocked"
            summary = f"guardrail blocked action: {decision.reason}"
            next_context = "The previous action was blocked by guardrails. Choose a safer action."
        else:
            kind = "tool_error"
            summary = f"guardrail {decision.decision}: {decision.reason}"
            next_context = "The previous action needs guardrail-aware adjustment before retrying."
        if truncated:
            summary = f"{summary} (raw output truncated)"
            next_context = f"{next_context} The raw excerpt was truncated."
        return Feedback(
            kind=kind,
            summary=self._redact_text(summary),
            raw_excerpt=raw_excerpt,
            suggested_next_context=self._redact_text(next_context),
        )

    def _excerpt(self, text: str) -> tuple[str, bool]:
        redacted = self._redact_text(text)
        if len(redacted) <= self._max_excerpt_chars:
            return redacted, False
        return redacted[: self._max_excerpt_chars], True

    @staticmethod
    def _looks_like_test_failure(text: str) -> bool:
        return "assertionerror" in text.casefold() or "failed" in text.casefold()

    @staticmethod
    def _redact_text(text: str) -> str:
        return str(redact_secrets(text))
