from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _SafeLoopBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def _resolved_path(value: Path | str) -> Path:
    return Path(value).expanduser().resolve()


class HarnessConfig(_SafeLoopBaseModel):
    workspace: Path
    allowed_paths: list[Path] = Field(default_factory=list)
    blocked_paths: list[Path] = Field(default_factory=list)
    test_command: str
    lint_command: str | None = None
    build_command: str | None = None
    blocked_commands: list[str] = Field(default_factory=list)
    approval_required_commands: list[str] = Field(default_factory=list)
    llm_provider: Literal["mock", "deepseek"] = "mock"
    model: str | None = None
    credential_backend: Literal["keyring", "env", "dotenv"] = "keyring"
    max_steps: int = 10
    command_timeout_seconds: int = 60
    max_file_bytes: int = 200_000

    @field_validator("workspace", mode="before")
    @classmethod
    def _resolve_workspace(cls, value: Path | str) -> Path:
        return _resolved_path(value)


class RunRecord(_SafeLoopBaseModel):
    run_id: str
    task: str
    status: Literal["created", "running", "finished", "failed", "cancelled"]
    workspace: Path | None = None
    config_path: Path | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentAction(_SafeLoopBaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    expected_outcome: str


class ToolResult(_SafeLoopBaseModel):
    tool_name: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    summary: str
    duration_ms: int


class GuardrailDecision(_SafeLoopBaseModel):
    decision: Literal["allow", "deny", "escalate"]
    risk_level: Literal["low", "medium", "high", "critical"]
    reason: str
    matched_rule: str | None = None


class Feedback(_SafeLoopBaseModel):
    source: Literal["user", "guardrail", "system", "tool"]
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryEntry(_SafeLoopBaseModel):
    key: str
    value: str
    namespace: str = "default"


class Event(_SafeLoopBaseModel):
    type: str
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
