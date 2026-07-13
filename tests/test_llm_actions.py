import pytest

from safeloop.actions import ActionParseError, parse_action
from safeloop.llm.base import LLMRequest
from safeloop.llm.mock import MockLLMClient


def test_mock_llm_returns_scripted_actions():
    client = MockLLMClient(
        responses=[
            '{"tool_name":"read_file","arguments":{"path":"app.py"},"reason":"inspect","expected_outcome":"content"}'
        ]
    )

    raw = client.complete(LLMRequest(task="fix", feedback=[], memories=[], events=[]))

    assert '"read_file"' in raw


def test_mock_llm_raises_clear_error_when_script_is_exhausted():
    client = MockLLMClient(responses=[])

    with pytest.raises(RuntimeError, match="exhausted"):
        client.complete(LLMRequest(task="fix", feedback=[], memories=[], events=[]))


def test_parse_action_accepts_known_tool():
    action = parse_action(
        '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
        allowed_tools={"run_tests"},
    )

    assert action.tool_name == "run_tests"
    assert action.reason == "verify"


def test_parse_action_rejects_unknown_tool():
    with pytest.raises(ActionParseError, match="unknown tool"):
        parse_action(
            '{"tool_name":"delete_database","arguments":{},"reason":"bad","expected_outcome":"gone"}',
            allowed_tools={"read_file"},
        )


def test_parse_action_rejects_invalid_json():
    with pytest.raises(ActionParseError, match="valid JSON"):
        parse_action("not json", allowed_tools={"read_file"})


def test_parse_action_rejects_missing_required_field():
    with pytest.raises(ActionParseError, match="missing required field"):
        parse_action(
            '{"tool_name":"read_file","arguments":{},"reason":"inspect"}',
            allowed_tools={"read_file"},
        )


def test_parse_action_rejects_non_object_json():
    with pytest.raises(ActionParseError, match="JSON object"):
        parse_action(
            '[{"tool_name":"read_file","arguments":{},"reason":"inspect","expected_outcome":"content"}]',
            allowed_tools={"read_file"},
        )
