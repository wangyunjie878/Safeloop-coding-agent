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
    redaction_secret_env_vars: list[str] = Field(default_factory=lambda: ["DEEPSEEK_API_KEY"])

    @field_validator("workspace", mode="before")
    @classmethod
    def _resolve_workspace(cls, value: Path | str) -> Path:
        return _resolved_path(value)


class RunRecord(_SafeLoopBaseModel):
    id: str
    task: str
    workspace: Path
    status: Literal["created", "running", "waiting_approval", "finished", "stopped", "failed"] = "created"
    current_step: int = 0
    max_steps: int = 10
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    @field_validator("workspace", mode="before")
    @classmethod
    def _resolve_workspace(cls, value: Path | str) -> Path:
        return _resolved_path(value)


class AgentAction(_SafeLoopBaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    expected_outcome: str


class ToolResult(_SafeLoopBaseModel):
    tool_name: str
    success: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    summary: str = ""
    duration_ms: int = 0


class GuardrailDecision(_SafeLoopBaseModel):
    decision: Literal["allow", "deny", "require_approval"]
    risk_level: Literal["low", "medium", "high", "critical"]
    reason: str
    matched_rule: str = ""


class Feedback(_SafeLoopBaseModel):
    kind: Literal[
        "test_failure",
        "syntax_error",
        "timeout",
        "guardrail_blocked",
        "tool_error",
        "parse_error",
        "generic_failure",
    ]
    summary: str
    raw_excerpt: str = ""
    suggested_next_context: str = ""


class MemoryEntry(_SafeLoopBaseModel):
    id: str
    scope: Literal["project", "run", "user"]
    tags: list[str] = Field(default_factory=list)
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_run_id: str | None = None


class Event(_SafeLoopBaseModel):
    run_id: str
    step: int
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
