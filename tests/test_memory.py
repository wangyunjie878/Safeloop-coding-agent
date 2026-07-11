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
