from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from safeloop.config import HarnessConfig


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    config: HarnessConfig
    run_id: str
    step: int
