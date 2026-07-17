from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from safeloop.config import HarnessConfig


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    config: HarnessConfig
    run_id: str
    step: int
    approval_granted: bool = False


class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str
    description: str
    arguments_schema: dict[str, object]


class UnknownToolError(Exception):
    pass
