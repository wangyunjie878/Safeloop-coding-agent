from __future__ import annotations

from pathlib import Path

import pytest

from safeloop import cli


class _FakeDeepSeekClient:
    created: list[dict[str, object]] = []

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.requests: list[str] = []
        _FakeDeepSeekClient.created.append(
            {"api_key": api_key, "model": model, "base_url": base_url, "client": self}
        )

    def complete(self, request) -> str:
        self.requests.append(request.task)
        return (
            '{"tool_name":"finish","arguments":{"message":"deepseek run complete"},'
            '"reason":"done","expected_outcome":"stop"}'
        )


class _WorkspaceDeepSeekClient:
    created: list["_WorkspaceDeepSeekClient"] = []

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.responses = [
            (
                '{"tool_name":"write_file","arguments":{"path":"count_primes.py",'
                '"content":"print(17)\\n"},"reason":"create requested code",'
                '"expected_outcome":"file is written"}'
            ),
            (
                '{"tool_name":"finish","arguments":{"message":"created count_primes.py"},'
                '"reason":"task complete","expected_outcome":"stop"}'
            ),
        ]
        _WorkspaceDeepSeekClient.created.append(self)

    def complete(self, request) -> str:
        return self.responses.pop(0)


class _InterruptingDeepSeekClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def complete(self, request) -> str:
        raise KeyboardInterrupt


def _write_config(tmp_path: Path, *, credential_backend: str = "env", model: str = "deepseek-v4-pro") -> Path:
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {tmp_path}\n"
        "test_command: python -c \"print('ok')\"\n"
        "llm_provider: deepseek\n"
        f"credential_backend: {credential_backend}\n"
        f"model: {model}\n"
        "max_steps: 3\n",
        encoding="utf-8",
    )
    return config_path


@pytest.fixture(autouse=True)
def reset_fake_deepseek() -> None:
    _FakeDeepSeekClient.created.clear()


def test_run_command_can_use_deepseek_with_user_configured_env_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-cli")
    monkeypatch.setattr(cli, "DeepSeekClient", _FakeDeepSeekClient)
    config_path = _write_config(tmp_path)

    exit_code = cli.main(
        [
            "run",
            "--config",
            str(config_path),
            "--task",
            "fix the calculator",
            "--llm",
            "deepseek",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "final_status: finished" in output
    assert "sk-test-cli" not in output
    assert _FakeDeepSeekClient.created[0]["api_key"] == "sk-test-cli"
    assert _FakeDeepSeekClient.created[0]["model"] == "deepseek-v4-pro"


def test_run_command_reports_missing_deepseek_key_without_secret_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(cli, "DeepSeekClient", _FakeDeepSeekClient)
    config_path = _write_config(tmp_path)

    exit_code = cli.main(
        [
            "run",
            "--config",
            str(config_path),
            "--task",
            "fix",
            "--llm",
            "deepseek",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing DeepSeek API key" in captured.err
    assert "DEEPSEEK_API_KEY" in captured.err
    assert "sk-" not in captured.out + captured.err
    assert _FakeDeepSeekClient.created == []


def test_chat_command_runs_one_deepseek_turn_then_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-chat-cli")
    monkeypatch.setattr(cli, "DeepSeekClient", _FakeDeepSeekClient)
    inputs = iter(["inspect failing tests", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    config_path = _write_config(tmp_path, model="deepseek-v4-flash")

    exit_code = cli.main(
        [
            "chat",
            "--config",
            str(config_path),
            "--llm",
            "deepseek",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SafeLoop CLI 对话模式" in output
    assert "deepseek run complete" in output
    assert "final_status:" not in output
    assert _FakeDeepSeekClient.created[0]["model"] == "deepseek-v4-flash"
    assert _FakeDeepSeekClient.created[0]["client"].requests == ["inspect failing tests"]


def test_chat_without_config_uses_current_directory_as_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-chat-cli")
    monkeypatch.setattr(cli, "DeepSeekClient", _WorkspaceDeepSeekClient)
    inputs = iter(["write a prime counter", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    exit_code = cli.main(["chat", "--llm", "deepseek", "--credential-backend", "env"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert (tmp_path / "count_primes.py").read_text(encoding="utf-8") == "print(17)\n"
    assert "created count_primes.py" in output
    assert "修改的文件:" in output
    assert "final_status:" not in output


def test_chat_ctrl_c_stops_current_task_without_exiting_safeloop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-chat-cli")
    monkeypatch.setattr(cli, "DeepSeekClient", _InterruptingDeepSeekClient)
    inputs = iter(["long task", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    exit_code = cli.main(["chat", "--llm", "deepseek", "--credential-backend", "env"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "正在执行任务" in output
    assert "已终止当前任务，SafeLoop 仍在运行。" in output
