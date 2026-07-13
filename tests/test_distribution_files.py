from pathlib import Path

import yaml


def test_readme_has_required_sections():
    text = Path("README.md").read_text(encoding="utf-8")

    for heading in [
        "Project Overview",
        "Installation",
        "Running",
        "Distribution",
        "Credential Security",
        "Safety Boundaries",
        "Directory Structure",
        "Testing",
        "CI/CD",
        "Known Limits",
    ]:
        assert heading in text


def test_readme_has_chinese_delivery_sections_and_distribution_notes():
    text = Path("README.md").read_text(encoding="utf-8")

    for phrase in [
        "项目简介",
        "安装",
        "运行",
        "分发命令",
        "目录结构",
        "安全边界说明",
        "获取方式",
        "Key 安全配置",
        "已知限制",
    ]:
        assert phrase in text


def test_readme_install_and_run_flow_is_chinese_first():
    text = Path("README.md").read_text(encoding="utf-8")

    for phrase in [
        "普通使用安装",
        "开发或跑测试安装",
        "进入你要让 agent 操作的代码目录",
        "python -m pip install -e .",
        "python -m pip install -e \".[dev]\"",
        "python -m safeloop chat --llm deepseek",
        "Docker 不是日常 CLI 使用的主入口",
    ]:
        assert phrase in text

    for english_only_phrase in [
        "Run the deterministic mechanism demo",
        "Run one CLI task with the offline mock LLM",
        "Configure a user-owned DeepSeek key",
        "Start the simple opencode-style terminal loop",
        "Chat mode prints Chinese user-facing output",
    ]:
        assert english_only_phrase not in text


def test_gitlab_ci_has_unit_test_job():
    data = yaml.load(Path(".gitlab-ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert "unit-test" in data
    assert "python -m pytest" in data["unit-test"]["script"]


def test_github_actions_runs_tests_and_docker_build():
    data = yaml.load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert set(data["on"]) == {"push", "pull_request"}
    assert "paths-ignore" not in data["on"]["push"]
    assert "paths-ignore" not in data["on"]["pull_request"]

    jobs = data["jobs"]
    test_runs = [step["run"] for step in jobs["test"]["steps"] if "run" in step]
    demo_runs = [step["run"] for step in jobs["demo"]["steps"] if "run" in step]
    docker_runs = [step["run"] for step in jobs["docker-build"]["steps"] if "run" in step]

    assert "python -m pytest" in test_runs
    assert "python -m safeloop demo" in demo_runs
    assert "docker build -t safeloop-agent ." in docker_runs


def test_dockerfile_starts_webui():
    text = Path("Dockerfile").read_text(encoding="utf-8")

    assert 'CMD ["python", "-m", "safeloop", "web", "--host", "0.0.0.0", "--port", "8000"]' in text


def test_dockerignore_excludes_local_credentials():
    ignored = set(Path(".dockerignore").read_text(encoding="utf-8").splitlines())

    assert ".env" in ignored
    assert ".env.*" in ignored
    assert ".safeloop" in ignored
