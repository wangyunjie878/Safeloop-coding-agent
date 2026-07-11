from pathlib import Path

import pytest

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction
from safeloop.tools.base import ToolContext
from safeloop.tools.dispatcher import ToolDispatcher


def make_context(workspace: Path, **config_overrides) -> ToolContext:
    config_kwargs = {
        "workspace": workspace,
        "test_command": 'python -c "print(\'tests-from-config\')"',
        "blocked_commands": ["git push"],
        "approval_required_commands": ["pip install"],
    }
    config_kwargs.update(config_overrides)
    config = HarnessConfig(**config_kwargs)
    return ToolContext(config=config, run_id="run-1", step=1)


def make_dispatcher(workspace: Path, **config_overrides) -> ToolDispatcher:
    return ToolDispatcher(make_context(workspace, **config_overrides))


def test_available_tools_contains_required_names(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    assert dispatcher.available_tools() == {
        "list_files",
        "read_file",
        "write_file",
        "patch_file",
        "run_command",
        "run_tests",
        "save_memory",
        "load_memory",
        "finish",
    }


def test_tool_schemas_are_serializable_and_named(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    schemas = dispatcher.tool_schemas()

    assert {schema["name"] for schema in schemas} == dispatcher.available_tools()
    for schema in schemas:
        assert isinstance(schema["arguments_schema"], dict)
        assert "description" in schema


def test_dispatch_routes_read_file(tmp_path: Path):
    workspace = tmp_path
    (workspace / "notes.txt").write_text("hello\nworld\n", encoding="utf-8")
    dispatcher = make_dispatcher(workspace)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="read_file",
            arguments={"path": "notes.txt"},
            reason="inspect file",
            expected_outcome="source content",
        )
    )

    assert result.success is True
    assert "hello" in result.stdout


def test_dispatch_routes_write_and_patch_file(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    write_result = dispatcher.dispatch(
        AgentAction(
            tool_name="write_file",
            arguments={"path": "app.py", "content": "print('hello')\n"},
            reason="create file",
            expected_outcome="file written",
        )
    )
    patch_result = dispatcher.dispatch(
        AgentAction(
            tool_name="patch_file",
            arguments={"path": "app.py", "old": "hello", "new": "world"},
            reason="update file",
            expected_outcome="file patched",
        )
    )

    assert write_result.success is True
    assert patch_result.success is True
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "print('world')\n"


def test_dispatch_routes_run_tests(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path, test_command='python -c "print(\'ok\')"')

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="run_tests",
            arguments={},
            reason="run suite",
            expected_outcome="test output",
        )
    )

    assert result.success is True
    assert result.stdout == "ok\n"


def test_dispatch_routes_run_command_timeout_argument(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="run_command",
            arguments={"command": 'python -c "import time; time.sleep(1)"', "timeout_seconds": 0.01},
            reason="run command",
            expected_outcome="timeout",
        )
    )

    assert result.success is False
    assert "timeout after 0.01 seconds" in result.summary


def test_unknown_tool_returns_failed_result(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="missing_tool",
            arguments={},
            reason="unknown",
            expected_outcome="failure",
        )
    )

    assert result.success is False
    assert "unknown tool" in result.summary.lower()
    assert result.tool_name == "missing_tool"


def test_missing_required_argument_returns_failed_result(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="read_file",
            arguments={},
            reason="missing path",
            expected_outcome="failure",
        )
    )

    assert result.success is False
    assert "missing" in result.summary.lower()


def test_wrong_argument_type_returns_failed_result(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="read_file",
            arguments={"path": 123},
            reason="bad type",
            expected_outcome="failure",
        )
    )

    assert result.success is False
    assert "type" in result.summary.lower()


def test_finish_returns_success_and_message_in_stdout(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="finish",
            arguments={"message": "done now"},
            reason="stop",
            expected_outcome="finished",
        )
    )

    assert result.success is True
    assert result.summary == "finished"
    assert result.stdout == "done now"


def test_memory_tools_report_unavailable(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    save_result = dispatcher.dispatch(
        AgentAction(
            tool_name="save_memory",
            arguments={"content": "x"},
            reason="save",
            expected_outcome="failure",
        )
    )
    load_result = dispatcher.dispatch(
        AgentAction(
            tool_name="load_memory",
            arguments={"query": "x"},
            reason="load",
            expected_outcome="failure",
        )
    )

    assert save_result.success is False
    assert save_result.summary == "memory store unavailable"
    assert load_result.success is False
    assert load_result.summary == "memory store unavailable"


def test_memory_tools_report_unavailable_without_arguments(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    save_result = dispatcher.dispatch(
        AgentAction(
            tool_name="save_memory",
            arguments={},
            reason="save",
            expected_outcome="failure",
        )
    )
    load_result = dispatcher.dispatch(
        AgentAction(
            tool_name="load_memory",
            arguments={},
            reason="load",
            expected_outcome="failure",
        )
    )

    assert save_result.success is False
    assert save_result.summary == "memory store unavailable"
    assert load_result.success is False
    assert load_result.summary == "memory store unavailable"


def test_dispatch_catches_tool_exceptions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dispatcher = make_dispatcher(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(dispatcher._file_tools, "read_file", boom)

    result = dispatcher.dispatch(
        AgentAction(
            tool_name="read_file",
            arguments={"path": "notes.txt"},
            reason="boom",
            expected_outcome="failure",
        )
    )

    assert result.success is False
    assert "kaboom" in result.summary
