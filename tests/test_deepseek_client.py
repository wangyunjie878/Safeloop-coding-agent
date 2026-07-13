from __future__ import annotations

import json

import httpx
import pytest

from safeloop.llm import LLMRequest
from safeloop.llm.deepseek import DeepSeekClient, DeepSeekClientError
from safeloop.models import Event, Feedback, MemoryEntry


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
    assert seen["body"]["model"] == "deepseek-v4-flash"
    assert seen["body"]["messages"][0]["role"] == "system"
    assert "exactly one JSON object" in seen["body"]["messages"][0]["content"]
    assert seen["body"]["messages"][1] == {"role": "user", "content": "Run the tests"}
    assert seen["body"]["stream"] is False


def test_deepseek_client_accepts_explicit_model_override():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "deepseek-v4-pro"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", model="deepseek-v4-pro", http_client=http_client)

    assert client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[])) == "ok"


def test_deepseek_client_default_timeout_allows_slow_model_responses():
    client = DeepSeekClient(api_key="sk-test")

    try:
        assert client.http_client.timeout.read == 600.0
    finally:
        client.http_client.close()


def test_deepseek_client_prompt_requests_chinese_user_facing_finish_messages():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    assert client.complete(LLMRequest(task="写一份快速排序示例", feedback=[], memories=[], events=[])) == "ok"

    system_prompt = seen["body"]["messages"][0]["content"]
    assert "中文" in system_prompt
    assert "finish" in system_prompt
    assert "message" in system_prompt


def test_deepseek_client_prompt_describes_single_json_tool_action_contract():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    assert client.complete(
        LLMRequest(
            task="Fix the project",
            feedback=[],
            memories=[],
            events=[],
            tool_schemas=[{"name": "read_file"}, {"name": "patch_file"}, {"name": "run_tests"}],
        )
    ) == "ok"

    messages = seen["body"]["messages"]
    system_prompt = messages[0]["content"]
    context_text = messages[2]["content"]
    assert "exactly one JSON object" in system_prompt
    assert "tool_name" in system_prompt
    assert "patch_file" in context_text
    assert "run_tests" in context_text


def test_deepseek_client_serializes_redacted_agent_context():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)
    request = LLMRequest(
        task="Fix the failing test",
        feedback=[
            Feedback(
                kind="test_failure",
                summary="pytest failed",
                raw_excerpt="AssertionError",
                suggested_next_context="inspect calculator.py",
            )
        ],
        memories=[
            MemoryEntry(
                id="memory-1",
                scope="project",
                tags=["tests"],
                content="Use pytest for this project.",
            )
        ],
        events=[
            Event(
                run_id="run-1",
                step=1,
                type="tool_result",
                payload={"summary": "failed", "note": "Do not expose sk-live-secret12345678."},
            )
        ],
        tool_schemas=[{"name": "run_tests", "arguments": {}}],
    )

    assert client.complete(request) == "ok"

    body = seen["body"]
    context_message = body["messages"][2]
    context_text = context_message["content"]
    assert context_message["role"] == "user"
    assert "test_failure" in context_text
    assert "Use pytest" in context_text
    assert "tool_result" in context_text
    assert "run_tests" in context_text
    assert "sk-live-secret12345678" not in context_text
    assert "[REDACTED]" in context_text


def test_deepseek_client_redacts_configured_known_secret_from_task_and_context():
    seen: dict[str, object] = {}
    known_secret = "alpha-token-123"

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)
    request = LLMRequest(
        task=f"Fix issue involving {known_secret}",
        memories=[
            MemoryEntry(
                id="memory-1",
                scope="project",
                tags=["tests"],
                content=f"Use pytest and avoid {known_secret}.",
            )
        ],
        events=[Event(run_id="run-1", step=1, type="note", payload={"value": known_secret})],
        tool_schemas=[{"name": "finish", "arguments": {}}],
        known_secrets=[known_secret],
    )

    assert client.complete(request) == "ok"

    body_text = json.dumps(seen["body"])
    assert known_secret not in body_text
    assert "[REDACTED]" in body_text


def test_deepseek_client_raises_clear_error_on_non_2xx_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    with pytest.raises(DeepSeekClientError, match="401"):
        client.complete(LLMRequest(task="Explain", feedback=[], memories=[], events=[]))


def test_deepseek_client_wraps_read_timeout_as_clear_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow response", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = DeepSeekClient(api_key="sk-test", http_client=http_client)

    with pytest.raises(DeepSeekClientError, match="timed out"):
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
