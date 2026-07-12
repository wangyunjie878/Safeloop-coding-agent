# SafeLoop

## Project Overview

SafeLoop is a bounded coding-agent harness with a deterministic mock LLM, explicit tool guardrails, feedback events, and a small FastAPI WebUI. The default examples run offline and do not require provider credentials.

## Installation

Use Python 3.11 or newer:

```bash
python -m pip install -e ".[dev]"
```

## Running

Run the deterministic mechanism demo:

```bash
python -m safeloop demo
```

Start the WebUI locally:

```bash
make web
# or: python -m safeloop web --host 0.0.0.0 --port 8000
```

## Distribution

Build and run the Docker image:

```bash
docker build -t safeloop-agent .
docker run --rm -p 8000:8000 safeloop-agent
```

The container starts the WebUI on `0.0.0.0:8000` in mock mode.

## Credential Security

The demo, tests, and Docker startup use the mock LLM. Keep real provider keys outside source control, prefer the credential manager or environment injection, and never place secrets in config files, logs, images, or CI output.

## Safety Boundaries

Configured workspace paths, allowed paths, blocked commands, timeouts, and approval/guardrail checks constrain tool execution. SafeLoop is a harness and does not grant permission to bypass repository, operating-system, or provider policies.

## Directory Structure

```text
safeloop/   Core models, state machine, tools, CLI, and WebUI
tests/      Unit and integration tests
samples/    Offline demo workspace
```

## Testing

```bash
make test
# equivalent: python -m pytest -v
```

## CI/CD

GitHub Actions runs on every push and pull request, including documentation-only changes. It runs the unit tests, the offline demo, and the Docker build. GitLab CI provides a `unit-test` job running `python -m pytest`.

Workflow definitions are checked in at `.github/workflows/ci.yml` and `.gitlab-ci.yml`. After the branch is pushed, CI evidence is available from the repository's GitHub Actions page. No hosted WebUI deployment URL is currently recorded in this repository.

## Known Limits

The current command path supports the mock LLM only. The WebUI is intentionally minimal, and Docker distribution is local build/run support rather than a published registry image or hosted service.
