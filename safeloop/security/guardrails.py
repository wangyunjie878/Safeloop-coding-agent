from __future__ import annotations

from pathlib import Path
from typing import Iterable

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction, GuardrailDecision


class GuardrailError(Exception):
    pass


_DEFAULT_BLOCKED_PATH_PARTS = {
    ".env",
    "id_rsa",
    "id_ed25519",
    ".ssh",
    "history",
}
_DEFAULT_BLOCKED_PATH_SEQUENCES = ((".git", "config"),)
_DEFAULT_BLOCKED_COMMAND_PATTERNS = (
    "rm -rf /",
    "git push",
    "docker push",
    "kubectl delete",
    "drop database",
    "shutdown",
    "reboot",
)


def _resolve_candidate(workspace: Path, candidate: Path | str) -> Path:
    candidate_path = Path(candidate).expanduser()
    if candidate_path.is_absolute():
        return candidate_path.resolve()
    return (workspace / candidate_path).resolve()


def is_path_within_workspace(workspace: Path, candidate: Path) -> bool:
    workspace_path = Path(workspace).expanduser().resolve()
    candidate_path = _resolve_candidate(workspace_path, candidate)
    try:
        candidate_path.relative_to(workspace_path)
    except ValueError:
        return False
    return True


def _candidate_parts(workspace: Path, candidate: Path | str) -> tuple[str, ...]:
    workspace_path = Path(workspace).expanduser().resolve()
    candidate_path = _resolve_candidate(workspace_path, candidate)
    try:
        relative = candidate_path.relative_to(workspace_path)
    except ValueError:
        return tuple(part.casefold() for part in candidate_path.parts)
    return tuple(part.casefold() for part in relative.parts)


def _contains_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    if len(sequence) > len(parts):
        return False
    for start in range(len(parts) - len(sequence) + 1):
        if parts[start : start + len(sequence)] == sequence:
            return True
    return False


def _path_hits_default_blocklist(workspace: Path, candidate: Path | str) -> str | None:
    parts = _candidate_parts(workspace, candidate)
    for part in parts:
        if part in _DEFAULT_BLOCKED_PATH_PARTS:
            return part
    for sequence in _DEFAULT_BLOCKED_PATH_SEQUENCES:
        if _contains_sequence(parts, sequence):
            return "/".join(sequence)
    return None


def _path_within_any(workspace: Path, candidate: Path | str, anchors: Iterable[Path | str]) -> bool:
    if not anchors:
        return True

    workspace_path = Path(workspace).expanduser().resolve()
    candidate_path = _resolve_candidate(workspace_path, candidate)

    for anchor in anchors:
        anchor_path = _resolve_candidate(workspace_path, anchor)
        try:
            candidate_path.relative_to(anchor_path)
        except ValueError:
            continue
        return True
    return False


def _command_matches(command: str, patterns: Iterable[str]) -> str | None:
    normalized = " ".join(command.casefold().split())
    for pattern in patterns:
        normalized_pattern = " ".join(pattern.casefold().split())
        if normalized_pattern and normalized_pattern in normalized:
            return pattern
    return None


class GuardrailEngine:
    def __init__(self, config: HarnessConfig):
        self._config = config

    def evaluate(self, action: AgentAction) -> GuardrailDecision:
        if action.tool_name in {"read_file", "write_file"}:
            return self._evaluate_path_action(action)
        if action.tool_name in {"run_command", "run_tests"}:
            return self._evaluate_command_action(action)
        return self._evaluate_relevant_arguments(action)

    def _evaluate_relevant_arguments(self, action: AgentAction) -> GuardrailDecision:
        decisions: list[GuardrailDecision] = []

        if action.arguments.get("path") is not None:
            decisions.append(self._evaluate_path_action(action))

        if action.arguments.get("command") is not None:
            decisions.append(self._evaluate_command_action(action))

        for decision_name in ("deny", "require_approval"):
            for decision in decisions:
                if decision.decision == decision_name:
                    return decision

        return GuardrailDecision(
            decision="allow",
            risk_level="low",
            reason="no guardrail rule matched",
            matched_rule="",
        )

    def _evaluate_path_action(self, action: AgentAction) -> GuardrailDecision:
        path_value = action.arguments.get("path")
        if path_value is None:
            return GuardrailDecision(
                decision="allow",
                risk_level="low",
                reason="path argument missing",
                matched_rule="",
            )

        candidate = _resolve_candidate(self._config.workspace, path_value)
        if not is_path_within_workspace(self._config.workspace, candidate):
            return GuardrailDecision(
                decision="deny",
                risk_level="high",
                reason="path escapes workspace",
                matched_rule="workspace_escape",
            )

        if not _path_within_any(self._config.workspace, candidate, self._config.allowed_paths):
            return GuardrailDecision(
                decision="deny",
                risk_level="high",
                reason="path is not covered by allowed_paths",
                matched_rule="allowed_paths",
            )

        blocked_config_path = self._match_blocked_config_path(candidate)
        if blocked_config_path is not None:
            return GuardrailDecision(
                decision="deny",
                risk_level="high",
                reason="path matches blocked_paths",
                matched_rule=f"blocked_paths:{blocked_config_path}",
            )

        blocked_rule = _path_hits_default_blocklist(self._config.workspace, candidate)
        if blocked_rule is not None:
            return GuardrailDecision(
                decision="deny",
                risk_level="high",
                reason="path matches blocked secret location",
                matched_rule=f"blocked_path:{blocked_rule}",
            )

        return GuardrailDecision(
            decision="allow",
            risk_level="low",
            reason="path allowed",
            matched_rule="",
        )

    def _match_blocked_config_path(self, candidate: Path | str) -> str | None:
        for blocked in self._config.blocked_paths:
            blocked_path = _resolve_candidate(self._config.workspace, blocked)
            try:
                candidate_path = _resolve_candidate(self._config.workspace, candidate)
                candidate_path.relative_to(blocked_path)
            except ValueError:
                continue
            return str(blocked_path)
        return None

    def _evaluate_command_action(self, action: AgentAction) -> GuardrailDecision:
        command_value = action.arguments.get("command")
        if command_value is None:
            return GuardrailDecision(
                decision="allow",
                risk_level="low",
                reason="command argument missing",
                matched_rule="",
            )

        command = str(command_value)
        blocked_rule = _command_matches(
            command,
            (*_DEFAULT_BLOCKED_COMMAND_PATTERNS, *self._config.blocked_commands),
        )
        if blocked_rule is not None:
            return GuardrailDecision(
                decision="deny",
                risk_level="critical",
                reason="command matches blocked pattern",
                matched_rule=f"blocked_command:{blocked_rule}",
            )

        approval_rule = _command_matches(command, self._config.approval_required_commands)
        if approval_rule is not None:
            return GuardrailDecision(
                decision="require_approval",
                risk_level="medium",
                reason="command requires approval",
                matched_rule=f"approval_required_command:{approval_rule}",
            )

        return GuardrailDecision(
            decision="allow",
            risk_level="low",
            reason="command allowed",
            matched_rule="",
        )
