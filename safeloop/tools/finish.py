from __future__ import annotations

from safeloop.models import ToolResult

from .base import ToolContext


def _tool_result(tool_name: str, success: bool, summary: str, **kwargs) -> ToolResult:
    return ToolResult(tool_name=tool_name, success=success, summary=summary, **kwargs)


class FinishTools:
    def __init__(self, context: ToolContext):
        self._context = context

    def finish(self, message: str = "") -> ToolResult:
        return _tool_result("finish", True, "finished", stdout=message)
