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
