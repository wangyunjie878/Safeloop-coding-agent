from __future__ import annotations

import json

import httpx
import pytest

from safeloop.llm import LLMRequest
from safeloop.llm.deepseek import DeepSeekClient, DeepSeekClientError


def test_deepseek_client_posts_expected_payload_and_returns_content():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"tool_name":"run_tests"}'}}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    result = client.complete(LLMRequest(task="Run the tests", feedback=[], memories=[], events=[]))

    assert result == '{"tool_name":"run_tests"}'
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["authorization"] == "Bearer sk-test"
    assert seen["body"] == {
        "model": "deepseek-v4-flash",
        "messages": [
            {
                "role": "system",
                "content": "You are SafeLoop. Respond with JSON actions only.",
            },
            {"role": "user", "content": "Run the tests"},
        ],
        "stream": False,
    }


def test_deepseek_client_accepts_explicit_model_override():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "deepseek-v4-pro"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", model="deepseek-v4-pro", http_client=http_client)

    assert client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[])) == "ok"


def test_deepseek_client_raises_clear_error_on_non_2xx_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    with pytest.raises(DeepSeekClientError, match="401"):
        client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[]))


def test_deepseek_client_raises_clear_error_on_malformed_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    with pytest.raises(DeepSeekClientError, match="Malformed"):
        client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[]))


def test_deepseek_client_raises_clear_error_on_non_json_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    with pytest.raises(DeepSeekClientError, match="Malformed DeepSeek response"):
        client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[]))
