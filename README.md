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

Run one CLI task with the offline mock LLM:

```bash
python -m safeloop run --config samples/python_buggy_calculator/safeloop.yml --task "fix calculator" --llm mock
```

Configure a user-owned DeepSeek key, then run a real-model task:

```bash
python -m safeloop credentials set --provider deepseek
cd path/to/your/project
python -m safeloop run --task "fix the failing tests" --llm deepseek
```

Start the simple opencode-style terminal loop:

```bash
cd path/to/your/project
python -m safeloop chat --llm deepseek
```

Chat mode prints Chinese user-facing output by default. While a task is running, press `Ctrl+C` to stop only the current task and return to the `safeloop>` prompt. Use `exit` or `quit` to leave SafeLoop.

By default, `run` and `chat` use the directory you are currently in as the workspace. Use `--workspace path/to/project` when you want to target a different directory, or `--config safeloop.yml` when you need project-specific settings such as a custom test command, blocked commands, timeouts, or model defaults.

For machines where OS keyring is not available, use an environment variable or a local `.env` file that is never committed:

```bash
set DEEPSEEK_API_KEY=your-key-here
python -m safeloop chat --llm deepseek --credential-backend env
python -m safeloop chat --llm deepseek --credential-backend dotenv --dotenv-path .env
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

The demo, tests, CI, and Docker startup use the mock LLM by default. Real DeepSeek usage is opt-in and uses user-provided credentials. Keep provider keys outside source control, prefer the credential manager or environment injection, and never place secrets in config files, logs, images, or CI output.

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

Workflow definitions are checked in at `.github/workflows/ci.yml` and `.gitlab-ci.yml`. PR #7 CI evidence includes GitHub Actions run #4, which passed on commit `efa6659`: https://github.com/wangyunjie878/Safeloop-coding-agent/actions/runs/29193389510. No hosted WebUI deployment URL is currently recorded in this repository.

## Known Limits

The CLI supports mock and DeepSeek-backed runs. The `chat` command is intentionally simple: each user message starts one bounded harness run, prints a Chinese user-facing summary, and waits for the next message. DeepSeek calls use a 600-second default timeout for longer code-generation turns. The `run` command still prints mechanism events for deterministic demos and grading evidence. The WebUI is intentionally minimal, and Docker distribution is local build/run support rather than a published registry image or hosted service.
