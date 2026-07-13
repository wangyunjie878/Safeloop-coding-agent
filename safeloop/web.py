from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from safeloop.config import ConfigError, HarnessConfig, collect_runtime_redaction_secrets, load_config
from safeloop.demo import DEMO_RESPONSES, _sample_source
from safeloop.events import EventLogStore
from safeloop.llm.mock import MockLLMClient
from safeloop.run_manager import RunManager, RunNotFoundError
from safeloop.security.redaction import redact_secrets
from safeloop.state_machine import AgentStateMachine


_DEFAULT_MOCK_FINISH_RESPONSE = (
    '{"tool_name":"finish","arguments":{"message":"mock run complete"},'
    '"reason":"default mock response","expected_outcome":"stop"}'
)


class RunRequest(BaseModel):
    task: str
    config_path: str
    mock_responses: list[str] = Field(default_factory=list)


class DemoRequest(BaseModel):
    task: str = "Fix the buggy calculator using the feedback loop."


def _run_with_manager(
    manager: RunManager,
    store: EventLogStore,
    run_configs: dict[str, HarnessConfig],
    task: str,
    config: HarnessConfig,
    mock_responses: list[str],
) -> dict[str, object]:
    if config.llm_provider != "mock":
        raise HTTPException(status_code=400, detail="web api only supports mock llm runs")

    responses = mock_responses or [_DEFAULT_MOCK_FINISH_RESPONSE]
    machine = AgentStateMachine(
        run_manager=manager,
        event_store=store,
        llm_client=MockLLMClient(responses),
    )
    run = machine.run(task, config)
    run_configs[run.id] = config
    return _run_response(run, config)


def _run_response(run, config: HarnessConfig) -> dict[str, object]:
    payload = run.model_dump(mode="json") | {"run_id": run.id}
    redacted = redact_secrets(payload, known_secrets=collect_runtime_redaction_secrets(config))
    if not isinstance(redacted, dict):
        raise HTTPException(status_code=500, detail="could not serialize run")
    return redacted


def _load_config_for_api(config_path: str) -> HarnessConfig:
    try:
        return load_config(config_path)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_app() -> FastAPI:
    app = FastAPI(title="SafeLoop")
    store = EventLogStore()
    manager = RunManager(event_store=store)
    run_configs: dict[str, HarnessConfig] = {}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (
            "<!doctype html>"
            "<html><head><title>SafeLoop</title></head>"
            "<body><main><h1>SafeLoop</h1>"
            "<p>Minimal task submission and run status WebUI.</p>"
            "</main></body></html>"
        )

    @app.post("/api/runs")
    def create_run(request: RunRequest) -> dict[str, object]:
        config = _load_config_for_api(request.config_path)
        return _run_with_manager(manager, store, run_configs, request.task, config, request.mock_responses)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        try:
            run = manager.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        config = run_configs[run_id]
        return _run_response(run, config)

    @app.get("/api/runs/{run_id}/events")
    def get_events(run_id: str) -> list[dict[str, object]]:
        try:
            manager.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        return [event.model_dump(mode="json") for event in store.list(run_id)]

    @app.post("/api/demo")
    def run_demo(request: DemoRequest) -> dict[str, object]:
        sample_source = _sample_source()
        with tempfile.TemporaryDirectory(prefix="safeloop-web-demo-") as temp_dir:
            workspace = Path(temp_dir) / "python_buggy_calculator"
            shutil.copytree(sample_source, workspace)
            config_path = workspace / "safeloop.yml"
            config_path.write_text(
                f"workspace: {workspace}\n"
                'test_command: python -c "import calculator; assert calculator.subtract(4, 2) == 2"\n'
                "llm_provider: mock\n"
                "allowed_paths:\n"
                "  - .\n"
                "blocked_commands:\n"
                "  - git push\n"
                "command_timeout_seconds: 10\n"
                "max_steps: 8\n",
                encoding="utf-8",
            )
            config = load_config(config_path)
            return _run_with_manager(manager, store, run_configs, request.task, config, DEMO_RESPONSES)

    return app
