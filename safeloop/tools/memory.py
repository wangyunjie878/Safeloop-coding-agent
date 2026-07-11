from __future__ import annotations

from safeloop.models import ToolResult

from .base import ToolContext


def _tool_result(tool_name: str, success: bool, summary: str, **kwargs) -> ToolResult:
    return ToolResult(tool_name=tool_name, success=success, summary=summary, **kwargs)


class MemoryTools:
    def __init__(self, context: ToolContext):
        self._context = context

    def save_memory(self, content: str) -> ToolResult:
        return _tool_result("save_memory", False, "memory store unavailable")

    def load_memory(self, query: str) -> ToolResult:
        return _tool_result("load_memory", False, "memory store unavailable")
