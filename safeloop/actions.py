from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from safeloop.models import AgentAction


class ActionParseError(ValueError):
    pass


def parse_action(raw: str, allowed_tools: set[str]) -> AgentAction:
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ActionParseError("action must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ActionParseError("action must be a JSON object")

    required_fields = {"tool_name", "arguments", "reason", "expected_outcome"}
    missing_fields = sorted(required_fields - payload.keys())
    if missing_fields:
        raise ActionParseError(f"missing required field: {missing_fields[0]}")

    tool_name = payload["tool_name"]
    if tool_name not in allowed_tools:
        raise ActionParseError(f"unknown tool: {tool_name}")

    try:
        return AgentAction.model_validate(payload)
    except ValidationError as exc:
        raise ActionParseError("action does not match AgentAction schema") from exc
