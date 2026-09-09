from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

from safeloop.models import AgentAction, ToolResult
from safeloop.security.guardrails import GuardrailEngine

from .base import ToolContext


_IGNORED_CHANGE_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".safeloop",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}


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
    changed_files: list[str] | None = None,
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        summary=summary,
        duration_ms=duration_ms,
        changed_files=changed_files or [],
    )


def _snapshot_workspace(workspace: Path) -> dict[str, tuple[int, int]]:
    root = workspace.resolve()
    snapshot: dict[str, tuple[int, int]] = {}
    for current_dir, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = [
            name
            for name in directory_names
            if name not in _IGNORED_CHANGE_DIRECTORIES and not (Path(current_dir) / name).is_symlink()
        ]
        for name in file_names:
            path = Path(current_dir) / name
            try:
                if path.is_symlink():
                    continue
                stat = path.stat()
                relative_path = path.relative_to(root).as_posix()
            except (OSError, ValueError):
                continue
            snapshot[relative_path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _changed_workspace_files(
    before: dict[str, tuple[int, int]],
    workspace: Path,
) -> list[str]:
    after = _snapshot_workspace(workspace)
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


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
    if decision.decision == "require_approval" and context.approval_granted:
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
    workspace_before = _snapshot_workspace(context.config.workspace)

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
            changed_files=_changed_workspace_files(workspace_before, context.config.workspace),
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
            changed_files=_changed_workspace_files(workspace_before, context.config.workspace),
        )
    except OSError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _tool_result(
            tool_name,
            False,
            f"failed to run command: {command}",
            exit_code=None,
            stderr=str(exc),
            duration_ms=duration_ms,
            changed_files=_changed_workspace_files(workspace_before, context.config.workspace),
        )


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
