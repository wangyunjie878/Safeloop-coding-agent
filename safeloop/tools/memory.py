from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from safeloop.config import collect_runtime_redaction_secrets
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
        self._reject_secret_entry_fields(tags=tags, content=content, source_run_id=source_run_id)
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

    def _reject_secret_entry_fields(
        self,
        tags: list[str],
        content: str,
        source_run_id: str | None,
    ) -> None:
        values = [content, *tags]
        if source_run_id is not None:
            values.append(source_run_id)
        for value in values:
            redacted = redact_secrets(value, known_secrets=self._known_secrets)
            if redacted != value:
                raise MemoryStoreError("memory entry appears to contain a secret")

    def _redact_entry(self, entry: MemoryEntry) -> MemoryEntry:
        entry_id = str(redact_secrets(entry.id, known_secrets=self._known_secrets))
        content = redact_secrets(entry.content, known_secrets=self._known_secrets)
        tags = [str(redact_secrets(tag, known_secrets=self._known_secrets)) for tag in entry.tags]
        source_run_id = (
            str(redact_secrets(entry.source_run_id, known_secrets=self._known_secrets))
            if entry.source_run_id is not None
            else None
        )
        return entry.model_copy(
            update={
                "id": entry_id,
                "content": content,
                "tags": tags,
                "source_run_id": source_run_id,
            }
        )


class MemoryTools:
    def __init__(self, context: ToolContext):
        self._context = context
        self._store = MemoryStore(
            context.config.workspace,
            known_secrets=collect_runtime_redaction_secrets(context.config),
        )

    def save_memory(self, content: str) -> ToolResult:
        if not content.strip():
            return _tool_result("save_memory", False, "content is required")
        try:
            entry = self._store.save(
                scope="project",
                tags=["agent"],
                content=content,
                source_run_id=self._context.run_id,
            )
        except MemoryStoreError as exc:
            return _tool_result("save_memory", False, str(exc))
        return _tool_result(
            "save_memory",
            True,
            "memory saved",
            stdout=json.dumps(entry.model_dump(mode="json"), ensure_ascii=False),
        )

    def load_memory(self, query: str) -> ToolResult:
        try:
            entries = self._store.query(scope="project")
        except MemoryStoreError as exc:
            return _tool_result("load_memory", False, str(exc))
        filtered = self._filter_entries(entries, query)
        return _tool_result(
            "load_memory",
            True,
            f"loaded {len(filtered)} memory entries",
            stdout=json.dumps([entry.model_dump(mode="json") for entry in filtered], ensure_ascii=False),
        )

    @staticmethod
    def _filter_entries(entries: list[MemoryEntry], query: str) -> list[MemoryEntry]:
        needle = query.casefold().strip()
        if not needle:
            return entries
        results: list[MemoryEntry] = []
        for entry in entries:
            haystack = " ".join([entry.content, *entry.tags, entry.source_run_id or ""]).casefold()
            if needle in haystack:
                results.append(entry)
        return results
