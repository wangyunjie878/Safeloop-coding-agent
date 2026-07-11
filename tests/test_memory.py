import json
from pathlib import Path

import pytest

from safeloop.tools.memory import MemoryStore, MemoryStoreError


def test_memory_store_saves_and_queries_by_tag(tmp_path: Path):
    store = MemoryStore(tmp_path)

    entry = store.save(
        scope="project",
        tags=["tests", "python"],
        content="Use python -m pytest for this project.",
        source_run_id="run-1",
    )

    results = store.query(scope="project", tags=["tests"])

    assert results == [entry]
    assert results[0].content.startswith("Use python")


def test_memory_store_missing_file_returns_empty(tmp_path: Path):
    store = MemoryStore(tmp_path)

    assert store.load_all() == []


def test_memory_store_rejects_secret_content(tmp_path: Path):
    store = MemoryStore(tmp_path)

    with pytest.raises(MemoryStoreError, match="secret"):
        store.save(scope="project", tags=["key"], content="DEEPSEEK_API_KEY=sk-live-secret12345678")

    assert store.load_all() == []
    assert not (tmp_path / ".safeloop" / "memory.json").exists()


def test_memory_store_rejects_and_redacts_configured_known_secrets(tmp_path: Path):
    known_secret = "alpha-token-123"
    store = MemoryStore(tmp_path, known_secrets=[known_secret])

    with pytest.raises(MemoryStoreError, match="secret"):
        store.save(scope="project", tags=["key"], content=f"token={known_secret}")

    memory_path = tmp_path / ".safeloop" / "memory.json"
    memory_path.parent.mkdir(parents=True)
    memory_path.write_text(
        json.dumps(
            [
                {
                    "id": "legacy-entry",
                    "scope": "project",
                    "tags": ["key"],
                    "content": f"token={known_secret}",
                }
            ]
        ),
        encoding="utf-8",
    )

    loaded = store.load_all()
    queried = store.query(scope="project")

    assert loaded[0].content == "token=[REDACTED]"
    assert queried[0].content == "token=[REDACTED]"


def test_memory_store_clear_removes_entries(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.save(scope="project", tags=["tests"], content="Run tests before finishing.")

    store.clear()

    assert store.load_all() == []


def test_memory_store_persists_entries_across_instances(tmp_path: Path):
    first = MemoryStore(tmp_path)
    entry = first.save(scope="project", tags=["style"], content="Keep patches small.")

    second = MemoryStore(tmp_path)

    assert second.load_all() == [entry]


def test_memory_store_query_filters_scope_and_tag_intersection(tmp_path: Path):
    store = MemoryStore(tmp_path)
    project_entry = store.save(scope="project", tags=["tests"], content="Use pytest.")
    store.save(scope="run", tags=["tests"], content="Temporary run note.")
    store.save(scope="project", tags=["docs"], content="Update README.")

    assert store.query(scope="project", tags=["tests"]) == [project_entry]
    assert store.query(tags=["docs", "missing"])[0].content == "Update README."
