from __future__ import annotations

import json

import httpx

from safeloop.llm.base import LLMRequest
from safeloop.security.redaction import redact_secrets


class DeepSeekClientError(RuntimeError):
    pass


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
        self.http_client = http_client or httpx.Client()

    def complete(self, request: LLMRequest) -> str:
        response = self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": self._build_messages(request),
                "stream": False,
            },
        )

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
                "content": "You are SafeLoop. Respond with JSON actions only.",
            },
            {"role": "user", "content": request.task},
        ]
        context = {
            "feedback": [item.model_dump(mode="json") for item in request.feedback],
            "memories": [item.model_dump(mode="json") for item in request.memories],
            "events": [item.model_dump(mode="json") for item in request.events],
            "tool_schemas": request.tool_schemas,
        }
        if any(context.values()):
            redacted_context = redact_secrets(context)
            redacted = json.dumps(redacted_context, ensure_ascii=False, sort_keys=True)
            messages.append(
                {
                    "role": "user",
                    "content": f"SafeLoop run context JSON:\n{redacted}",
                }
            )
        return messages
