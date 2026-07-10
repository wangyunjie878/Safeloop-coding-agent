from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import Event
from .security.redaction import redact_secrets


class EventLogStore:
    def __init__(self, known_secrets: Iterable[str] | None = None) -> None:
        self._events_by_run_id: dict[str, list[Event]] = defaultdict(list)
        self._known_secrets = [secret for secret in (known_secrets or []) if secret]

    def add_known_secrets(self, known_secrets: Iterable[str] | None) -> None:
        if known_secrets is None:
            return

        seen = set(self._known_secrets)
        for secret in known_secrets:
            if secret and secret not in seen:
                self._known_secrets.append(secret)
                seen.add(secret)

    def append(self, event: Event) -> Event:
        stored = event.model_copy(
            deep=True,
            update={"payload": redact_secrets(event.payload, known_secrets=self._known_secrets)},
        )
        self._events_by_run_id[stored.run_id].append(stored)
        return stored.model_copy(deep=True)

    def list(self, run_id: str) -> list[Event]:
        return [event.model_copy(deep=True) for event in self._events_by_run_id.get(run_id, [])]
