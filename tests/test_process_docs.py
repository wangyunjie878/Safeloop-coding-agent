from pathlib import Path


def test_spec_process_contains_required_sections():
    text = Path("SPEC_PROCESS.md").read_text(encoding="utf-8")

    for phrase in [
        "brainstorming 关键节点",
        "关键迭代",
        "冷启动验证",
        "SPEC / PLAN 修订",
    ]:
        assert phrase in text


def test_agent_log_contains_task_entries():
    text = Path("AGENT_LOG.md").read_text(encoding="utf-8")

    assert "Task" in text
    assert "Superpowers" in text
    assert "commit" in text.lower()


def test_reflection_marks_human_owned_report():
    text = Path("REFLECTION.md").read_text(encoding="utf-8")

    assert "Human-Owned Reflection" in text
    assert "TDD" in text
    assert "Superpowers" in text
