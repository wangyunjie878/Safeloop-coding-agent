from __future__ import annotations

import httpx

from safeloop.llm.base import LLMRequest


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
                "messages": [
                    {
                        "role": "system",
                        "content": "You are SafeLoop. Respond with JSON actions only.",
                    },
                    {"role": "user", "content": request.task},
                ],
                "stream": False,
            },
        )

        if response.status_code < 200 or response.status_code >= 300:
            raise DeepSeekClientError(f"DeepSeek request failed with status {response.status_code}")

        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekClientError("Malformed DeepSeek response payload") from exc

