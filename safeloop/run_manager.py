from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .config import HarnessConfig, collect_runtime_redaction_secrets
from .events import EventLogStore
from .models import Event, RunRecord


class RunNotFoundError(LookupError):
    pass


class RunManager:
    def __init__(self, event_store: EventLogStore | None = None) -> None:
        self._event_store = event_store or EventLogStore()
        self._runs: dict[str, RunRecord] = {}

    @property
    def event_store(self) -> EventLogStore:
        return self._event_store

    def create_run(self, task: str, config: HarnessConfig) -> RunRecord:
        self._event_store.add_known_secrets(collect_runtime_redaction_secrets(config))
        run = RunRecord(
            id=str(uuid4()),
            task=task,
            workspace=config.workspace,
            status="created",
            max_steps=config.max_steps,
        )
        self._runs[run.id] = run
        self._event_store.append(
            Event(
                run_id=run.id,
                step=run.current_step,
                type="run_created",
                payload={
                    "run_id": run.id,
                    "task": task,
                    "workspace": str(run.workspace),
                    "status": run.status,
                    "max_steps": run.max_steps,
                },
            )
        )
        return run.model_copy()

    def update_status(self, run_id: str, status: str, reason: str | None = None) -> RunRecord:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(f"run not found: {run_id}")

        run.status = status
        if status in {"finished", "stopped", "failed"}:
            run.finished_at = datetime.now(timezone.utc)

        payload: dict[str, object] = {"run_id": run_id, "status": status}
        if reason is not None:
            payload["reason"] = reason

        self._event_store.append(
            Event(
                run_id=run_id,
                step=run.current_step,
                type="state_changed",
                payload=payload,
            )
        )
        return run.model_copy()

    def get_run(self, run_id: str) -> RunRecord:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(f"run not found: {run_id}")
        return run.model_copy()
