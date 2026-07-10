from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import HarnessConfig


class ConfigError(ValueError):
    pass


def resolve_workspace(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _resolve_path_list(values: Any, workspace: Path, field_name: str) -> list[Path]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ConfigError(f"{field_name} must be a list of paths")

    resolved: list[Path] = []
    for value in values:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = workspace / candidate
        resolved.append(candidate.resolve())
    return resolved


def _normalize_config(data: dict[str, Any], source: Path) -> dict[str, Any]:
    if "workspace" not in data:
        raise ConfigError(f"{source}: missing required field workspace")

    workspace = resolve_workspace(data["workspace"])
    if not workspace.exists():
        raise ConfigError(f"workspace does not exist: {workspace}")

    normalized = dict(data)
    normalized["workspace"] = workspace
    normalized["allowed_paths"] = _resolve_path_list(data.get("allowed_paths"), workspace, "allowed_paths")
    normalized["blocked_paths"] = _resolve_path_list(data.get("blocked_paths"), workspace, "blocked_paths")
    return normalized


def _format_validation_error(error: ValidationError) -> str:
    pieces = []
    for item in error.errors():
        loc = ".".join(str(part) for part in item["loc"])
        pieces.append(f"{loc}: {item['msg']}")
    return "; ".join(pieces)


def load_config(path: Path | str) -> HarnessConfig:
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"could not read config: {config_path}") from exc

    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_path}: invalid YAML") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: config must be a mapping")

    normalized = _normalize_config(data, config_path)

    try:
        return HarnessConfig.model_validate(normalized)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(exc)) from exc
