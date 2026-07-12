from pathlib import Path

from fastapi.testclient import TestClient

from safeloop.cli import main
from safeloop.web import create_app


def test_health_endpoint():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_page_contains_product_name():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "SafeLoop" in response.text


def test_create_run_and_fetch_events(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {tmp_path}\n"
        "test_command: python -c \"print('ok')\"\n"
        "llm_provider: mock\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    create_response = client.post(
        "/api/runs",
        json={
            "task": "verify",
            "config_path": str(config_path),
            "mock_responses": [
                '{"tool_name":"finish","arguments":{"message":"done"},"reason":"done","expected_outcome":"stop"}'
            ],
        },
    )

    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "finished"
    assert client.get(f"/api/runs/{run_id}/events").status_code == 200


def test_missing_run_returns_404():
    client = TestClient(create_app())

    response = client.get("/api/runs/missing")

    assert response.status_code == 404


def test_web_cli_calls_uvicorn_runner(monkeypatch):
    calls = []

    def fake_run(app_path: str, host: str, port: int, factory: bool) -> None:
        calls.append({"app_path": app_path, "host": host, "port": port, "factory": factory})

    monkeypatch.setattr("uvicorn.run", fake_run)

    result = main(["web", "--host", "0.0.0.0", "--port", "8000"])

    assert result == 0
    assert calls == [
        {
            "app_path": "safeloop.web:create_app",
            "host": "0.0.0.0",
            "port": 8000,
            "factory": True,
        }
    ]
