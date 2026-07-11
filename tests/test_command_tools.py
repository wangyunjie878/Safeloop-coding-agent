from pathlib import Path
import subprocess

import pytest

from safeloop.config import HarnessConfig
from safeloop.tools.base import ToolContext


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


def make_tools(workspace: Path, max_stream_chars: int = 4000, **config_overrides):
    from safeloop.tools.commands import CommandTools

    return CommandTools(make_context(workspace, **config_overrides), max_stream_chars=max_stream_chars)


def test_run_command_captures_stdout_and_exit_code(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command('python -c "print(\'hello from command\')"')

    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout == "hello from command\n"
    assert result.stderr == ""


def test_run_command_uses_config_workspace_as_cwd(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command('python -c "from pathlib import Path; print(Path.cwd())"')

    assert result.success is True
    assert result.stdout.strip() == str(tmp_path.resolve())


def test_run_command_blocks_dangerous_command_without_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tools = make_tools(tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for blocked commands")

    monkeypatch.setattr("safeloop.tools.commands.subprocess.run", boom)

    result = tools.run_command("rm -rf /")

    assert result.success is False
    assert result.exit_code is None
    assert "deny" in result.summary.lower() or "blocked" in result.summary.lower()


def test_run_command_requires_approval_without_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tools = make_tools(tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for approval-required commands")

    monkeypatch.setattr("safeloop.tools.commands.subprocess.run", boom)

    result = tools.run_command("pip install requests")

    assert result.success is False
    assert result.exit_code is None
    assert "require_approval" in result.summary


def test_run_tests_uses_configured_test_command(tmp_path: Path):
    tools = make_tools(tmp_path, test_command='python -c "print(\'configured tests\')"')

    result = tools.run_tests()

    assert result.success is True
    assert result.stdout == "configured tests\n"


def test_run_command_reports_timeout_and_preserves_output(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command(
        'python -c "import sys, time; sys.stdout.write(\'before-timeout\'); sys.stdout.flush(); time.sleep(2)"',
        timeout_seconds=0.1,
    )

    assert result.success is False
    assert result.exit_code is None
    assert "timeout" in result.summary.lower()
    assert "before-timeout" in result.stdout


def test_run_command_reports_nonzero_exit_and_streams(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command(
        'python -c "import sys; print(\'stdout-line\'); print(\'stderr-line\', file=sys.stderr); sys.exit(3)"'
    )

    assert result.success is False
    assert result.exit_code == 3
    assert result.stdout == "stdout-line\n"
    assert result.stderr == "stderr-line\n"


def test_run_command_truncates_stdout_and_stderr(tmp_path: Path):
    tools = make_tools(tmp_path, max_stream_chars=8)

    result = tools.run_command(
        'python -c "import sys; sys.stdout.write(\'0123456789ABCDEF\'); sys.stderr.write(\'fedcba9876543210\')"'
    )

    assert result.success is True
    assert result.stdout.startswith("01234567")
    assert "[truncated 8 chars]" in result.stdout
    assert result.stderr.startswith("fedcba98")
    assert "[truncated 8 chars]" in result.stderr
