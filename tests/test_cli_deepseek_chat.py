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
    assert "SafeLoop CLI chat" in output
    assert "final_status: finished" in output
    assert _FakeDeepSeekClient.created[0]["model"] == "deepseek-v4-flash"
    assert _FakeDeepSeekClient.created[0]["client"].requests == ["inspect failing tests"]
