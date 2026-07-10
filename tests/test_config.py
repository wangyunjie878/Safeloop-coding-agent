from pathlib import Path

import pytest

from safeloop.config import ConfigError, load_config, resolve_workspace


def test_load_config_applies_defaults(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "allowed_paths:\n"
        "  - .\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.workspace == workspace.resolve()
    assert config.llm_provider == "mock"
    assert config.credential_backend == "keyring"
    assert config.max_steps == 10
    assert config.command_timeout_seconds == 60
    assert config.max_file_bytes == 200_000
    assert config.redaction_secret_env_vars == ["DEEPSEEK_API_KEY"]
    assert config.allowed_paths == [workspace.resolve()]


def test_load_config_rejects_missing_workspace(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        "workspace: missing\n"
        "test_command: python -m pytest\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="workspace"):
        load_config(config_path)


def test_load_config_wraps_list_workspace_in_config_error(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        "workspace:\n"
        "  - bad\n"
        "test_command: python -m pytest\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="workspace"):
        load_config(config_path)


def test_load_config_wraps_invalid_path_list_values_in_config_error(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "allowed_paths:\n"
        "  -\n"
        "    - bad\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="allowed_paths"):
        load_config(config_path)


def test_load_config_rejects_absolute_allowed_path_outside_workspace(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "allowed_paths:\n"
        f"  - {outside}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="allowed_paths"):
        load_config(config_path)


def test_load_config_rejects_relative_allowed_path_escape(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "allowed_paths:\n"
        "  - ../outside\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="allowed_paths"):
        load_config(config_path)


def test_load_config_rejects_blocked_path_outside_workspace(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "blocked_paths:\n"
        f"  - {outside}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="blocked_paths"):
        load_config(config_path)


def test_load_config_rejects_workspace_when_it_is_a_file(tmp_path: Path):
    workspace_file = tmp_path / "workspace.txt"
    workspace_file.write_text("not a directory", encoding="utf-8")
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace_file}\n"
        "test_command: python -m pytest\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="workspace"):
        load_config(config_path)


def test_resolve_workspace_returns_resolved_path(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    assert resolve_workspace(workspace) == workspace.resolve()


def test_load_config_keeps_redaction_secret_env_var_names_not_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("SAFELOOP_RUNTIME_SECRET", "real-secret-value")
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "redaction_secret_env_vars:\n"
        "  - SAFELOOP_RUNTIME_SECRET\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.redaction_secret_env_vars == ["SAFELOOP_RUNTIME_SECRET"]
    assert "real-secret-value" not in config.model_dump_json()
