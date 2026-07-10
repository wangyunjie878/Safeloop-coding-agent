from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from safeloop.credentials import CredentialError, CredentialManager


class _FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


@pytest.fixture
def fake_keyring(monkeypatch: pytest.MonkeyPatch) -> _FakeKeyring:
    fake = _FakeKeyring()
    monkeypatch.setattr("safeloop.credentials.keyring", fake)
    return fake


def test_keyring_backend_can_set_get_status_and_clear(fake_keyring: _FakeKeyring):
    manager = CredentialManager(backend="keyring")

    manager.set_key("deepseek", "sk-test")

    assert manager.get_key("deepseek") == "sk-test"
    assert manager.status("deepseek") == {"provider": "deepseek", "status": "configured"}

    manager.clear_key("deepseek")

    assert manager.get_key("deepseek") is None
    assert manager.status("deepseek") == {"provider": "deepseek", "status": "missing"}


def test_keyring_backend_clear_propagates_unexpected_errors(monkeypatch: pytest.MonkeyPatch):
    class _ExplodingKeyring(_FakeKeyring):
        def delete_password(self, service: str, username: str) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr("safeloop.credentials.keyring", _ExplodingKeyring())
    manager = CredentialManager(backend="keyring")

    with pytest.raises(CredentialError, match="Failed to clear"):
        manager.clear_key("deepseek")


def test_status_never_exposes_key_material(fake_keyring: _FakeKeyring):
    manager = CredentialManager(backend="keyring")
    manager.set_key("deepseek", "sk-secret")

    status = manager.status("deepseek")

    assert "sk-secret" not in str(status)
    assert set(status) == {"provider", "status"}


def test_env_backend_reads_deepseek_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")

    manager = CredentialManager(backend="env")

    assert manager.get_key("deepseek") == "sk-env"
    assert manager.status("deepseek") == {"provider": "deepseek", "status": "configured"}


def test_dotenv_backend_reads_env_file(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("DEEPSEEK_API_KEY=sk-dotenv\n", encoding="utf-8")

    manager = CredentialManager(backend="dotenv", dotenv_path=env_path)

    assert manager.get_key("deepseek") == "sk-dotenv"
    assert manager.status("deepseek") == {"provider": "deepseek", "status": "configured"}


@pytest.mark.parametrize("backend", ["env", "dotenv"])
def test_read_only_backends_reject_set_and_clear(
    backend: str,
    tmp_path: Path,
):
    kwargs = {"dotenv_path": tmp_path / ".env"} if backend == "dotenv" else {}
    manager = CredentialManager(backend=backend, **kwargs)

    with pytest.raises(CredentialError, match="read-only"):
        manager.set_key("deepseek", "sk-test")

    with pytest.raises(CredentialError, match="read-only"):
        manager.clear_key("deepseek")


def test_empty_key_is_rejected(fake_keyring: _FakeKeyring):
    manager = CredentialManager(backend="keyring")

    with pytest.raises(CredentialError, match="Empty keys are invalid"):
        manager.set_key("deepseek", "")


def test_cli_credentials_status_does_not_print_key_material(
    tmp_path: Path,
):
    env_path = tmp_path / ".env"
    env_path.write_text("DEEPSEEK_API_KEY=sk-secret\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safeloop",
            "credentials",
            "status",
            "--provider",
            "deepseek",
            "--backend",
            "dotenv",
            "--dotenv-path",
            str(env_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "configured" in result.stdout
    assert "sk-secret" not in result.stdout
