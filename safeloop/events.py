from __future__ import annotations

from collections import defaultdict

from .models import Event
from .security.redaction import redact_secrets


class EventLogStore:
    def __init__(self) -> None:
        self._events_by_run_id: dict[str, list[Event]] = defaultdict(list)

    def append(self, event: Event) -> Event:
        stored = event.model_copy(update={"payload": redact_secrets(event.payload)})
        self._events_by_run_id[stored.run_id].append(stored)
        return stored

    def list(self, run_id: str) -> list[Event]:
        return [event.model_copy() for event in self._events_by_run_id.get(run_id, [])]
