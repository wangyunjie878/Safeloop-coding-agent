from __future__ import annotations

from collections.abc import Sequence

from safeloop.llm.base import LLMRequest


class MockLLMClient:
    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self._next_index = 0

    def complete(self, request: LLMRequest) -> str:
        if self._next_index >= len(self._responses):
            raise RuntimeError("mock LLM response script exhausted")

        response = self._responses[self._next_index]
        self._next_index += 1
        return response
