from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from safeloop.models import MemoryEntry, ToolResult
from safeloop.security.redaction import redact_secrets

from .base import ToolContext


class MemoryStoreError(Exception):
    pass


def _tool_result(tool_name: str, success: bool, summary: str, **kwargs) -> ToolResult:
    return ToolResult(tool_name=tool_name, success=success, summary=summary, **kwargs)


class MemoryStore:
    def __init__(
        self,
        workspace: Path | str,
        memory_path: Path | str | None = None,
        known_secrets: list[str] | None = None,
    ):
        self._workspace = Path(workspace).expanduser().resolve()
        self._memory_path = (
            Path(memory_path).expanduser().resolve()
            if memory_path is not None
            else self._workspace / ".safeloop" / "memory.json"
        )
        self._known_secrets = [secret for secret in (known_secrets or []) if secret]

    def save(
        self,
        scope: str,
        tags: list[str],
        content: str,
        source_run_id: str | None = None,
    ) -> MemoryEntry:
        self._reject_secret_content(content)
        entries = self.load_all()
        entry = MemoryEntry(
            id=str(uuid4()),
            scope=scope,
            tags=list(tags),
            content=content,
            source_run_id=source_run_id,
        )
        entries.append(entry)
        self._write_all(entries)
        return entry

    def query(self, scope: str | None = None, tags: list[str] | None = None) -> list[MemoryEntry]:
        requested_tags = set(tags or [])
        results: list[MemoryEntry] = []
        for entry in self.load_all():
            if scope is not None and entry.scope != scope:
                continue
            if requested_tags and not requested_tags.intersection(entry.tags):
                continue
            results.append(entry)
        return results

    def load_all(self) -> list[MemoryEntry]:
        if not self._memory_path.exists():
            return []
        try:
            raw_entries = json.loads(self._memory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MemoryStoreError(f"failed to load memory store: {exc}") from exc
        if not isinstance(raw_entries, list):
            raise MemoryStoreError("memory store must contain a JSON list")
        try:
            entries = [MemoryEntry.model_validate(item) for item in raw_entries]
        except ValidationError as exc:
            raise MemoryStoreError(f"invalid memory entry: {exc}") from exc
        return [self._redact_entry(entry) for entry in entries]

    def clear(self) -> None:
        if self._memory_path.exists():
            self._memory_path.unlink()

    def _write_all(self, entries: list[MemoryEntry]) -> None:
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [entry.model_dump(mode="json") for entry in entries]
        self._memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _reject_secret_content(self, content: str) -> None:
        redacted = redact_secrets(content, known_secrets=self._known_secrets)
        if redacted != content:
            raise MemoryStoreError("memory content appears to contain a secret")

    def _redact_entry(self, entry: MemoryEntry) -> MemoryEntry:
        content = redact_secrets(entry.content, known_secrets=self._known_secrets)
        return entry.model_copy(update={"content": content})


class MemoryTools:
    def __init__(self, context: ToolContext):
        self._context = context

    def save_memory(self, content: str) -> ToolResult:
        return _tool_result("save_memory", False, "memory store unavailable")

    def load_memory(self, query: str) -> ToolResult:
        return _tool_result("load_memory", False, "memory store unavailable")
