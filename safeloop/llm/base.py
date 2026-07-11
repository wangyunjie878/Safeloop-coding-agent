from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from safeloop.models import Event, Feedback, MemoryEntry


class LLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task: str
    feedback: list[Feedback] = Field(default_factory=list)
    memories: list[MemoryEntry] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    tool_schemas: list[dict[str, object]] = Field(default_factory=list)


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> str:
        ...
