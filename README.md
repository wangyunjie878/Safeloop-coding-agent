# SafeLoop

## Project Overview

SafeLoop is a bounded coding-agent harness with a deterministic mock LLM, explicit tool guardrails, feedback events, and a small FastAPI WebUI. The default examples run offline and do not require provider credentials.

## 项目简介

SafeLoop 是一个轻量级 Coding Agent Harness。它面向本地软件开发场景，核心能力是让 agent 在用户指定的 workspace 中读取文件、写入或 patch 代码、执行命令、运行测试，并根据工具结果或测试失败反馈调整下一步行动。项目默认使用 deterministic mock LLM 做离线机制演示和 CI 测试；真实 LLM 接入是可选能力，目前支持用户自带 DeepSeek key。

## Installation

Use Python 3.11 or newer:

```bash
python -m pip install -e ".[dev]"
```

## 安装

从 GitHub 获取源码后，在仓库根目录执行：

```bash
python -m pip install -e ".[dev]"
```

如果只想运行 Docker WebUI，可以跳过本地 Python 安装，直接使用下方“分发命令”中的 Docker build/run。

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

## 运行

推荐的 CLI 使用方式是先进入你要让 agent 操作的代码目录，再启动 chat：

```bash
cd path/to/your/project
python -m safeloop chat --llm deepseek
```

如果只是给老师展示核心机制，使用 mock LLM 演示即可，不需要真实 key：

```bash
python -m safeloop demo
```

如果要执行一次性任务：

```bash
python -m safeloop run --task "fix the failing tests" --llm deepseek
```

`chat` 和 `run` 默认把当前目录当作 workspace。也可以用 `--workspace path/to/project` 指向其他目录，或用 `--config safeloop.yml` 指定测试命令、超时、模型和安全边界。

## Distribution

Build and run the Docker image:

```bash
docker build -t safeloop-agent .
docker run --rm -p 8000:8000 safeloop-agent
```

The container starts the WebUI on `0.0.0.0:8000` in mock mode.

## 分发命令

### 获取方式

从 GitHub 克隆仓库：

```bash
git clone https://github.com/wangyunjie878/Safeloop-coding-agent.git
cd Safeloop-coding-agent
```

或者下载 GitHub 仓库的 ZIP 包后解压，进入项目根目录。

### Docker 分发产物

本项目提供 `Dockerfile` 作为容器分发配置。构建镜像：

```bash
docker build -t safeloop-agent .
```

运行容器：

```bash
docker run --rm -p 8000:8000 safeloop-agent
```

容器启动后会运行 WebUI，监听 `0.0.0.0:8000`，默认使用 mock LLM，不需要真实 API key。GitHub Actions 也会在 CI 中执行 Docker build，用于证明分发配置可构建。

### 本地 CLI 分发形态

本项目也可以作为本地 Python CLI 使用：

```bash
python -m pip install -e ".[dev]"
python -m safeloop --help
```

目标平台为 Python 3.11+ 环境。Windows 上如果没有 GNU Make，可以用 `python -m pytest` 替代 `make test`。

## Credential Security

The demo, tests, CI, and Docker startup use the mock LLM by default. Real DeepSeek usage is opt-in and uses user-provided credentials. Keep provider keys outside source control, prefer the credential manager or environment injection, and never place secrets in config files, logs, images, or CI output.

## Key 安全配置

真实 LLM key 由使用者自己提供，仓库内不包含任何真实凭据。推荐方式是写入操作系统 keyring：

```bash
python -m safeloop credentials set --provider deepseek
```

如果目标机器没有可用 keyring，可以临时使用环境变量：

```bash
set DEEPSEEK_API_KEY=your-key-here
python -m safeloop chat --llm deepseek --credential-backend env
```

也可以使用本地 `.env`，但 `.env` 必须留在本机，不得提交到 git、Docker 镜像或 CI 日志中：

```bash
python -m safeloop chat --llm deepseek --credential-backend dotenv --dotenv-path .env
```

CI、机制演示和 Docker 默认都使用 mock LLM，因此不需要配置真实 key。

## Safety Boundaries

Configured workspace paths, allowed paths, blocked commands, timeouts, and approval/guardrail checks constrain tool execution. SafeLoop is a harness and does not grant permission to bypass repository, operating-system, or provider policies.

## 安全边界说明

SafeLoop 的工具执行受 workspace 限制：文件读取、写入、patch 和命令执行默认只能发生在用户选择的工作目录中。路径逃逸、敏感文件、危险命令和超时命令会被拒绝或反馈给 agent。项目还会对事件日志、反馈和 provider 上下文中的已知 secret 做脱敏处理。

需要注意的是，SafeLoop 是教学型 harness，不是沙箱或权限隔离系统。它能减少误操作风险，但不能替代操作系统权限、容器隔离、代码审查或真实生产环境的安全策略。

## Directory Structure

```text
safeloop/   Core models, state machine, tools, CLI, and WebUI
tests/      Unit and integration tests
samples/    Offline demo workspace
```

## 目录结构

```text
safeloop/                 核心实现：模型、配置、状态机、工具、CLI、WebUI
safeloop/llm/             LLM 抽象、MockLLMClient、DeepSeek client
safeloop/tools/           文件、命令、测试、记忆、finish 等工具
safeloop/security/        护栏和脱敏逻辑
tests/                    单元测试与集成测试
samples/python_buggy_calculator/  mock LLM 机制演示样例
.github/workflows/ci.yml  GitHub Actions CI 配置
.gitlab-ci.yml            GitLab CI 兼容配置，包含 unit-test job
Dockerfile                Docker 分发配置
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

## 已知限制

- `chat` 是简化版 CLI，不是完整 opencode/Codex 复刻；每次用户输入会启动一个有步数上限的 harness run。
- WebUI 主要用于展示和 API smoke test，功能比 CLI 少。
- Docker 镜像默认运行 mock WebUI，不内置真实 LLM key。
- DeepSeek 调用依赖用户自己的 key 和网络环境；CI 不会调用真实 DeepSeek。
- Windows 本地如果没有 GNU Make，请使用 `python -m pytest` 替代 `make test`。
