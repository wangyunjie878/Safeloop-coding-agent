from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from safeloop.models import AgentAction, ToolResult

from .base import ToolContext, ToolSpec, UnknownToolError
from .commands import CommandTools
from .files import FileTools
from .finish import FinishTools
from .memory import MemoryTools


def _tool_result(tool_name: str, success: bool, summary: str, **kwargs: Any) -> ToolResult:
    return ToolResult(tool_name=tool_name, success=success, summary=summary, **kwargs)


@dataclass(frozen=True)
class _ToolEntry:
    spec: ToolSpec
    handler: Callable[..., ToolResult]
    required: tuple[str, ...]
    optional_types: dict[str, tuple[type[Any], ...]]
    defaults: dict[str, Any]


class ToolDispatcher:
    def __init__(self, context: ToolContext):
        self._context = context
        self._file_tools = FileTools(context)
        self._command_tools = CommandTools(context)
        self._memory_tools = MemoryTools(context)
        self._finish_tools = FinishTools(context)
        self._registry = self._build_registry()

    def _build_registry(self) -> dict[str, _ToolEntry]:
        return {
            "list_files": _ToolEntry(
                spec=ToolSpec(
                    name="list_files",
                    description="List files in a workspace directory",
                    arguments_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string", "default": "."}},
                        "required": [],
                    },
                ),
                handler=lambda **kwargs: self._file_tools.list_files(**kwargs),
                required=(),
                optional_types={"path": (str,)},
                defaults={"path": "."},
            ),
            "read_file": _ToolEntry(
                spec=ToolSpec(
                    name="read_file",
                    description="Read a file from the workspace",
                    arguments_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "start_line": {"type": "integer"},
                            "end_line": {"type": "integer"},
                        },
                        "required": ["path"],
                    },
                ),
                handler=lambda **kwargs: self._file_tools.read_file(**kwargs),
                required=("path",),
                optional_types={"path": (str,), "start_line": (int,), "end_line": (int,)},
                defaults={},
            ),
            "write_file": _ToolEntry(
                spec=ToolSpec(
                    name="write_file",
                    description="Write a file in the workspace",
                    arguments_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"],
                    },
                ),
                handler=lambda **kwargs: self._file_tools.write_file(**kwargs),
                required=("path", "content"),
                optional_types={"path": (str,), "content": (str,)},
                defaults={},
            ),
            "patch_file": _ToolEntry(
                spec=ToolSpec(
                    name="patch_file",
                    description="Replace text in a file in the workspace",
                    arguments_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
                        "required": ["path", "old", "new"],
                    },
                ),
                handler=lambda **kwargs: self._file_tools.patch_file(**kwargs),
                required=("path", "old", "new"),
                optional_types={"path": (str,), "old": (str,), "new": (str,)},
                defaults={},
            ),
            "run_command": _ToolEntry(
                spec=ToolSpec(
                    name="run_command",
                    description="Run a shell command in the workspace",
                    arguments_schema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "timeout_seconds": {"type": ["integer", "number"]},
                        },
                        "required": ["command"],
                    },
                ),
                handler=lambda **kwargs: self._command_tools.run_command(**kwargs),
                required=("command",),
                optional_types={"command": (str,), "timeout_seconds": (int, float)},
                defaults={},
            ),
            "run_tests": _ToolEntry(
                spec=ToolSpec(
                    name="run_tests",
                    description="Run the configured test command",
                    arguments_schema={"type": "object", "properties": {}, "required": []},
                ),
                handler=lambda **kwargs: self._command_tools.run_tests(**kwargs),
                required=(),
                optional_types={},
                defaults={},
            ),
            "save_memory": _ToolEntry(
                spec=ToolSpec(
                    name="save_memory",
                    description="Persist a memory entry",
                    arguments_schema={
                        "type": "object",
                        "properties": {"content": {"type": "string", "default": ""}},
                        "required": [],
                    },
                ),
                handler=lambda **kwargs: self._memory_tools.save_memory(**kwargs),
                required=(),
                optional_types={"content": (str,)},
                defaults={"content": ""},
            ),
            "load_memory": _ToolEntry(
                spec=ToolSpec(
                    name="load_memory",
                    description="Load matching memory entries",
                    arguments_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string", "default": ""}},
                        "required": [],
                    },
                ),
                handler=lambda **kwargs: self._memory_tools.load_memory(**kwargs),
                required=(),
                optional_types={"query": (str,)},
                defaults={"query": ""},
            ),
            "finish": _ToolEntry(
                spec=ToolSpec(
                    name="finish",
                    description="Mark the task finished",
                    arguments_schema={
                        "type": "object",
                        "properties": {"message": {"type": "string", "default": ""}},
                        "required": [],
                    },
                ),
                handler=lambda **kwargs: self._finish_tools.finish(**kwargs),
                required=(),
                optional_types={"message": (str,)},
                defaults={"message": ""},
            ),
        }

    def available_tools(self) -> set[str]:
        return set(self._registry)

    def tool_schemas(self) -> list[dict[str, object]]:
        return [entry.spec.model_dump() for entry in self._registry.values()]

    def dispatch(self, action: AgentAction) -> ToolResult:
        entry = self._registry.get(action.tool_name)
        if entry is None:
            return _tool_result(action.tool_name, False, f"unknown tool: {action.tool_name}")

        try:
            arguments = self._validate_arguments(action.tool_name, action.arguments, entry)
        except UnknownToolError:
            return _tool_result(action.tool_name, False, f"unknown tool: {action.tool_name}")
        except ValueError as exc:
            return _tool_result(action.tool_name, False, str(exc))

        try:
            return entry.handler(**arguments)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return _tool_result(action.tool_name, False, f"tool execution failed: {exc}")

    def _validate_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        entry: _ToolEntry,
    ) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError(f"invalid arguments for {tool_name}: expected object")

        parsed: dict[str, Any] = {}
        allowed_names = set(entry.required) | set(entry.optional_types)
        unexpected = sorted(set(arguments) - allowed_names)
        if unexpected:
            raise ValueError(f"unexpected argument(s) for {tool_name}: {', '.join(unexpected)}")

        for name in entry.required:
            if name not in arguments:
                raise ValueError(f"missing required argument for {tool_name}: {name}")
        for name, value in arguments.items():
            expected_types = entry.optional_types.get(name)
            if expected_types is None:
                continue
            if not self._value_matches_type(value, expected_types):
                raise ValueError(f"wrong type for {tool_name}.{name}: expected {self._describe_types(expected_types)}")
            parsed[name] = value

        for name, value in entry.defaults.items():
            parsed.setdefault(name, value)

        for name in entry.required:
            parsed[name] = arguments[name]

        if tool_name == "run_command" and isinstance(parsed.get("timeout_seconds"), bool):
            raise ValueError("wrong type for run_command.timeout_seconds: expected number")

        return parsed

    @staticmethod
    def _value_matches_type(value: Any, expected_types: tuple[type[Any], ...]) -> bool:
        if isinstance(value, bool):
            return bool in expected_types
        return isinstance(value, expected_types)

    @staticmethod
    def _describe_types(types: tuple[type[Any], ...]) -> str:
        names = []
        for item in types:
            if item is int:
                names.append("integer")
            elif item is float:
                names.append("number")
            elif item is str:
                names.append("string")
            else:
                names.append(item.__name__)
        return " or ".join(names)
