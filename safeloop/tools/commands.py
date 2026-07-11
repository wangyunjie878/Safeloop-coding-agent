from __future__ import annotations

import subprocess
import time

from safeloop.models import AgentAction, ToolResult
from safeloop.security.guardrails import GuardrailEngine

from .base import ToolContext


class CommandToolError(Exception):
    pass


def _tool_result(
    tool_name: str,
    success: bool,
    summary: str,
    *,
    exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    duration_ms: int = 0,
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        summary=summary,
        duration_ms=duration_ms,
    )


def _coerce_stream(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _truncate_stream(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    omitted = len(value) - max_chars
    return f"{value[:max_chars]}...[truncated {omitted} chars]"


def _guardrail_result(context: ToolContext, tool_name: str, command: str) -> ToolResult | None:
    action = AgentAction(
        tool_name=tool_name,
        arguments={"command": command},
        reason="command execution request",
        expected_outcome="command output",
    )
    decision = GuardrailEngine(context.config).evaluate(action)
    if decision.decision == "allow":
        return None
    return _tool_result(
        tool_name,
        False,
        f"guardrail {decision.decision}: {decision.reason}",
        stderr=decision.matched_rule,
    )


def _execute_command(
    tool_name: str,
    command: str,
    context: ToolContext,
    max_stream_chars: int,
    timeout: int,
) -> ToolResult:
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            cwd=context.config.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        stdout = _truncate_stream(_coerce_stream(completed.stdout), max_stream_chars)
        stderr = _truncate_stream(_coerce_stream(completed.stderr), max_stream_chars)
        duration_ms = int((time.perf_counter() - started) * 1000)
        success = completed.returncode == 0
        summary = "command completed" if success else f"command exited with code {completed.returncode}"
        return _tool_result(
            tool_name,
            success,
            summary,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = _truncate_stream(
            _coerce_stream(getattr(exc, "stdout", None) or getattr(exc, "output", None)),
            max_stream_chars,
        )
        stderr = _truncate_stream(_coerce_stream(getattr(exc, "stderr", None)), max_stream_chars)
        summary = f"command timeout after {timeout} seconds"
        if stdout or stderr:
            summary += " (partial output captured)"
        return _tool_result(
            tool_name,
            False,
            summary,
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
    except OSError as exc:
        raise CommandToolError(f"failed to run command: {command}") from exc


class CommandTools:
    def __init__(self, context: ToolContext, max_stream_chars: int = 4000):
        self._context = context
        self._max_stream_chars = max_stream_chars

    def run_command(self, command: str, timeout_seconds: int | None = None) -> ToolResult:
        guardrail_result = _guardrail_result(self._context, "run_command", command)
        if guardrail_result is not None:
            return guardrail_result

        timeout = self._context.config.command_timeout_seconds if timeout_seconds is None else timeout_seconds
        return _execute_command("run_command", command, self._context, self._max_stream_chars, timeout)

    def run_tests(self) -> ToolResult:
        command = self._context.config.test_command
        guardrail_result = _guardrail_result(self._context, "run_tests", command)
        if guardrail_result is not None:
            return guardrail_result
        timeout = self._context.config.command_timeout_seconds
        return _execute_command("run_tests", command, self._context, self._max_stream_chars, timeout)
