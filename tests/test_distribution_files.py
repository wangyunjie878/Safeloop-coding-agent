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
    data = yaml.safe_load(Path(".gitlab-ci.yml").read_text(encoding="utf-8"))

    assert "unit-test" in data


def test_github_actions_runs_tests_and_docker_build():
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "python -m pytest" in text
    assert "python -m safeloop demo" in text
    assert "docker build" in text


def test_dockerfile_starts_webui():
    text = Path("Dockerfile").read_text(encoding="utf-8")

    assert "python" in text
    assert "safeloop" in text
    assert "web" in text
