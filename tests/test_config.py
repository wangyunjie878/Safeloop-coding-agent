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


def test_resolve_workspace_returns_resolved_path(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    assert resolve_workspace(workspace) == workspace.resolve()
