from __future__ import annotations

import json

import httpx

from safeloop.llm.base import LLMRequest
from safeloop.security.redaction import redact_secrets


class DeepSeekClientError(RuntimeError):
    pass


_DEFAULT_TIMEOUT_SECONDS = 60.0


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client or httpx.Client(timeout=_DEFAULT_TIMEOUT_SECONDS)

    def complete(self, request: LLMRequest) -> str:
        try:
            response = self.http_client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": self._build_messages(request),
                    "stream": False,
                },
            )
        except httpx.TimeoutException as exc:
            raise DeepSeekClientError("DeepSeek request timed out; retry or use a shorter task") from exc
        except httpx.RequestError as exc:
            raise DeepSeekClientError(f"DeepSeek request failed: {exc}") from exc

        if response.status_code < 200 or response.status_code >= 300:
            raise DeepSeekClientError(f"DeepSeek request failed with status {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise DeepSeekClientError("Malformed DeepSeek response payload: response was not valid JSON") from exc

        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekClientError("Malformed DeepSeek response payload") from exc

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are SafeLoop, a coding agent harness. Respond with exactly one JSON object "
                    "and no Markdown. The JSON object must contain tool_name, arguments, reason, "
                    "and expected_outcome. Choose one available tool from the provided tool_schemas. "
                    "Use feedback from failed tools or tests to decide the next action."
                ),
            },
            {"role": "user", "content": str(redact_secrets(request.task, known_secrets=request.known_secrets))},
        ]
        context = {
            "feedback": [item.model_dump(mode="json") for item in request.feedback],
            "memories": [item.model_dump(mode="json") for item in request.memories],
            "events": [item.model_dump(mode="json") for item in request.events],
            "tool_schemas": request.tool_schemas,
        }
        if any(context.values()):
            redacted_context = redact_secrets(context, known_secrets=request.known_secrets)
            redacted = json.dumps(redacted_context, ensure_ascii=False, sort_keys=True)
            messages.append(
                {
                    "role": "user",
                    "content": f"SafeLoop run context JSON:\n{redacted}",
                }
            )
        return messages
