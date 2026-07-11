from __future__ import annotations

from pathlib import Path
import os

from safeloop.models import AgentAction, ToolResult
from safeloop.security.guardrails import GuardrailEngine

from .base import ToolContext


class FileToolError(Exception):
    pass


_EXCLUDED_DIR_NAMES = {".git", ".venv", "__pycache__", ".pytest_cache", ".safeloop"}
_SENSITIVE_PATH_NAMES = {".env"}


def _workspace_root(context: ToolContext) -> Path:
    return Path(context.config.workspace).expanduser().resolve()


def _resolve_relative_path(context: ToolContext, path: str) -> Path:
    workspace = _workspace_root(context)
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (workspace / candidate).resolve()


def _tool_result(tool_name: str, success: bool, summary: str, **kwargs) -> ToolResult:
    return ToolResult(tool_name=tool_name, success=success, summary=summary, **kwargs)


def _guardrail_result(context: ToolContext, tool_name: str, path: str) -> ToolResult | None:
    action = AgentAction(
        tool_name=tool_name,
        arguments={"path": path},
        reason="file tool path check",
        expected_outcome="workspace-bounded file access",
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


def _ensure_workspace_path(context: ToolContext, path: str, tool_name: str) -> Path | ToolResult:
    if Path(path).name in _SENSITIVE_PATH_NAMES:
        return _tool_result(tool_name, False, f"sensitive path rejected: {path}")

    guardrail_result = _guardrail_result(context, tool_name, path)
    if guardrail_result is not None:
        return guardrail_result

    candidate = _resolve_relative_path(context, path)
    workspace = _workspace_root(context)
    try:
        candidate.relative_to(workspace)
    except ValueError:
        return _tool_result(tool_name, False, "path escapes workspace")
    return candidate


def _is_binary_prefix(prefix: bytes) -> bool:
    return b"\x00" in prefix


class FileTools:
    def __init__(self, context: ToolContext):
        self._context = context

    def list_files(self, path: str = ".") -> ToolResult:
        candidate = _ensure_workspace_path(self._context, path, "list_files")
        if isinstance(candidate, ToolResult):
            return candidate
        if not candidate.exists():
            return _tool_result("list_files", False, f"path does not exist: {path}")
        if not candidate.is_dir():
            return _tool_result("list_files", False, f"path is not a directory: {path}")

        workspace = _workspace_root(self._context)
        relative_paths: list[str] = []
        for root, dirs, files in os.walk(candidate):
            dirs[:] = sorted(directory for directory in dirs if directory not in _EXCLUDED_DIR_NAMES)
            current_root = Path(root)
            for filename in sorted(files):
                if filename in _SENSITIVE_PATH_NAMES:
                    continue
                file_path = current_root / filename
                relative_paths.append(str(file_path.relative_to(workspace)))

        relative_paths.sort()
        stdout = "\n".join(relative_paths)
        if stdout:
            stdout += "\n"
        return _tool_result("list_files", True, f"listed {len(relative_paths)} path(s)", stdout=stdout)

    def read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> ToolResult:
        candidate = _ensure_workspace_path(self._context, path, "read_file")
        if isinstance(candidate, ToolResult):
            return candidate
        if not candidate.exists():
            return _tool_result("read_file", False, f"file does not exist: {path}")
        if not candidate.is_file():
            return _tool_result("read_file", False, f"path is not a file: {path}")

        max_bytes = self._context.config.max_file_bytes
        if candidate.stat().st_size > max_bytes:
            return _tool_result("read_file", False, f"file too large: {path}")

        with candidate.open("rb") as handle:
            prefix = handle.read(512)
        if _is_binary_prefix(prefix):
            return _tool_result("read_file", False, f"binary file rejected: {path}")

        text = candidate.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        if start_line is None and end_line is None:
            return _tool_result("read_file", True, f"read {path}", stdout=text)

        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else end_line
        if start < 1 or end < 1 or start > end or end > len(lines):
            return _tool_result("read_file", False, "invalid line range")

        sliced = "".join(lines[start - 1 : end])
        return _tool_result("read_file", True, f"read {path} lines {start}-{end}", stdout=sliced)

    def write_file(self, path: str, content: str) -> ToolResult:
        candidate = _ensure_workspace_path(self._context, path, "write_file")
        if isinstance(candidate, ToolResult):
            return candidate

        if candidate.exists() and not candidate.is_file():
            return _tool_result("write_file", False, f"path is not a file: {path}")

        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(content, encoding="utf-8")
        return _tool_result("write_file", True, f"wrote {path}")

    def patch_file(self, path: str, old: str, new: str) -> ToolResult:
        candidate = _ensure_workspace_path(self._context, path, "patch_file")
        if isinstance(candidate, ToolResult):
            return candidate
        if not candidate.exists():
            return _tool_result("patch_file", False, f"file does not exist: {path}")
        if not candidate.is_file():
            return _tool_result("patch_file", False, f"path is not a file: {path}")

        text = candidate.read_text(encoding="utf-8")
        occurrences = text.count(old)
        if occurrences != 1:
            return _tool_result("patch_file", False, "patch text must appear exactly once")

        candidate.write_text(text.replace(old, new, 1), encoding="utf-8")
        return _tool_result("patch_file", True, f"patched {path}")
