from pathlib import Path

import pytest

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction
from safeloop.tools.base import ToolContext
from safeloop.tools.files import FileToolError, FileTools


def make_config(workspace: Path, **overrides) -> HarnessConfig:
    data = {
        "workspace": workspace,
        "test_command": "python -m pytest",
        "allowed_paths": ["."],
    }
    data.update(overrides)
    return HarnessConfig(**data)


def make_tools(workspace: Path, **overrides) -> FileTools:
    context = ToolContext(config=make_config(workspace, **overrides), run_id="run-1", step=1)
    return FileTools(context)


def test_read_file_reads_inside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "notes.txt"
    file_path.write_text("hello\nworld\n", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.read_file("notes.txt")

    assert result.success is True
    assert "hello" in result.stdout


def test_read_file_rejects_workspace_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.read_file("../outside.txt")

    assert result.success is False
    assert "workspace" in result.summary.lower()


def test_read_file_rejects_env_file(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("SECRET=1", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.read_file(".env")

    assert result.success is False
    assert ".env" in result.summary


def test_read_file_rejects_large_file_before_full_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "large.txt"
    file_path.write_text("x" * 12, encoding="utf-8")

    tools = make_tools(workspace, max_file_bytes=5)
    result = tools.read_file("large.txt")

    assert result.success is False
    assert "too large" in result.summary.lower()


def test_read_file_rejects_binary_file(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "binary.bin"
    file_path.write_bytes(b"\x00\x01\x02")

    tools = make_tools(workspace)
    result = tools.read_file("binary.bin")

    assert result.success is False
    assert "binary" in result.summary.lower()


def test_read_file_supports_line_range(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "lines.txt"
    file_path.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.read_file("lines.txt", start_line=2, end_line=3)

    assert result.success is True
    assert result.stdout == "two\nthree\n"


def test_write_file_creates_nested_file_inside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    tools = make_tools(workspace)
    result = tools.write_file("nested/output.txt", "content")

    assert result.success is True
    assert (workspace / "nested" / "output.txt").read_text(encoding="utf-8") == "content"


def test_write_file_rejects_workspace_escape_without_writing(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"

    tools = make_tools(workspace)
    result = tools.write_file("../outside.txt", "content")

    assert result.success is False
    assert not outside.exists()


def test_patch_file_replaces_unique_text(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "app.py"
    file_path.write_text("print('hello')\n", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.patch_file("app.py", "hello", "world")

    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "print('world')\n"


def test_patch_file_rejects_ambiguous_match_and_leaves_file_unchanged(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "app.py"
    original = "alpha\nbeta\nalpha\n"
    file_path.write_text(original, encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.patch_file("app.py", "alpha", "omega")

    assert result.success is False
    assert file_path.read_text(encoding="utf-8") == original


def test_patch_file_rejects_zero_match_and_leaves_file_unchanged(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "app.py"
    original = "alpha\nbeta\n"
    file_path.write_text(original, encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.patch_file("app.py", "gamma", "omega")

    assert result.success is False
    assert file_path.read_text(encoding="utf-8") == original


def test_list_files_excludes_tooling_directories(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "visible.txt").write_text("ok", encoding="utf-8")
    (workspace / ".github").mkdir()
    (workspace / ".github" / "workflow.yml").write_text("name: ci", encoding="utf-8")
    for folder in [".git", ".venv", "__pycache__", ".pytest_cache", ".safeloop"]:
        target = workspace / folder
        target.mkdir()
        (target / "hidden.txt").write_text("secret", encoding="utf-8")

    tools = make_tools(workspace)
    result = tools.list_files(".")
    normalized_stdout = result.stdout.replace("\\", "/")
    listed_paths = normalized_stdout.splitlines()

    assert result.success is True
    assert "visible.txt" in normalized_stdout
    assert ".github/workflow.yml" in normalized_stdout
    for folder in [".git", ".venv", "__pycache__", ".pytest_cache", ".safeloop"]:
        assert all(not path.startswith(f"{folder}/") and path != folder for path in listed_paths)
