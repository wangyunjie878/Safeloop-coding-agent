# SafeLoop Coding Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个轻量级、教学型、本地运行的 Coding Agent Harness，使其能在用户指定 workspace 内通过 mock 或 DeepSeek LLM 执行“读代码 -> 调工具 -> 运行测试 -> 接收反馈 -> 自我修正 -> 停止”的完整闭环。

**Architecture:** SafeLoop 采用 Python 包作为核心实现，CLI 与 FastAPI WebUI 只是入口层。核心由配置加载、数据模型、事件日志、LLM 抽象、动作解析、护栏、工具分发、反馈分类、记忆存储和状态机构成；真实 LLM 可替换为 mock LLM，以便离线测试核心机制。所有危险动作拦截、反馈回灌、工具分发和停机条件必须由代码实现，不能依赖提示词。

**Tech Stack:** Python 3.11+、FastAPI、pytest、Pydantic、PyYAML、httpx、keyring、python-dotenv、Docker、GitHub Actions、GitLab CI 兼容配置。

## Global Constraints

- 在 `SPEC.md`、`PLAN.md` 完成并经过冷启动验证前，不得编写实现代码。
- 交付产物必须是自己编码实现的 harness 内核，不能调用 LangChain `AgentExecutor`、AutoGen、CrewAI、LlamaIndex agent 或宿主编码智能体的 agent runner。
- 核心机制必须能在移除真实 LLM 后，通过 `MockLLMClient` 进行确定性单元测试。
- 默认 LLM provider 是 `mock`；GitHub Actions 和 `.gitlab-ci.yml` 的 `unit-test` job 不需要真实 API key。
- 可选真实 provider 是 DeepSeek V4；具体 model id 由配置指定，代码不硬编码真实模型名。
- 真实 LLM key 默认存储在 OS keyring；`.env` 和环境变量仅作为开发、容器和 keyring 不可用场景的可选来源。
- 日志、事件、WebUI 和测试输出不得显示原始 API key、`.env` 内容、SSH key 或其他 secret。
- 默认单次 run 最多执行 10 个 LLM-action 步骤，并允许配置。
- 默认单个命令超时时间为 60 秒，并允许配置。
- 文件读取默认单文件上限为 200 KB；过大文件必须拒绝或摘要化。
- 所有文件和命令操作默认限制在用户选择的 workspace 内。
- TDD 是硬性要求：每个实现 task 先写失败测试并确认失败，再写最小实现，再重构。
- 每个 task 由一个新鲜 subagent 完成；每个 worktree 对应一个 PR。
- 每完成一个 task，必须更新 `PLAN.md` 中该 task 状态并附 commit hash，同时在 `AGENT_LOG.md` 记录技能、prompt/context、人工干预和经验。
- 最终仓库必须有一键测试命令：`make test`。
- 在 Windows 或其他未安装 GNU Make 的环境中，`make test` 的验证替代命令为 `python -m pytest`；CI 仍应使用明确的 Python 测试命令。
- CI 必须包括 GitHub Actions；最终交付还必须包含 `.gitlab-ci.yml`，其中 job 名称必须为 `unit-test`。
- Docker 是主要分发形态；README 必须写清 build/run 命令、key 安全配置方式、平台限制和已知限制。

---

## Pre-Implementation Gate: 冷启动验证

正式执行 Task 1 前，必须先完成以下验证：

1. 使用与主开发 agent 不同类型的第二个 agent。
2. 新开 session，不导入本对话、memory 或口头解释。
3. 只提供 `SPEC.md` 和 `PLAN.md`。
4. 指定它从 Task 1 和 Task 2 中任选 1-2 个自主推进，并明确：“遇到不确定之处即暂停询问，而非凭猜测继续。”
5. 将第二个 agent 暂停提问、误解、产出差距、暴露的 SPEC/PLAN 缺陷记录进 `SPEC_PROCESS.md`。
6. 根据冷启动反馈修订 `SPEC.md` 或 `PLAN.md` 后，才能进入实现。

---

## File Structure

### Project Root

- Create: `pyproject.toml` — Python 包元数据、依赖、pytest 配置。
- Create: `Makefile` — 一键命令：`make test`、`make demo`、`make web`。
- Create: `.gitignore` — 忽略 `.env`、虚拟环境、缓存、run 输出。
- Create: `README.md` — 项目简介、安装、运行、分发、安全边界、目录结构。
- Create: `Dockerfile` — 容器分发。
- Create: `.github/workflows/ci.yml` — GitHub Actions：测试、机制演示、Docker build。
- Create: `.gitlab-ci.yml` — 兼容最终清单，含 `unit-test` job。
- Create: `AGENT_LOG.md` — 实现过程日志。
- Create: `SPEC_PROCESS.md` — brainstorming、PLAN、冷启动验证过程记录。
- Modify: `PLAN.md` — 每完成 task 后标记状态和 commit hash。
- Modify: `SPEC.md` — 仅当冷启动或实现发现规约缺陷时修订。

### Package

- Create: `safeloop/__init__.py`
- Create: `safeloop/__main__.py`
- Create: `safeloop/cli.py`
- Create: `safeloop/models.py`
- Create: `safeloop/config.py`
- Create: `safeloop/events.py`
- Create: `safeloop/run_manager.py`
- Create: `safeloop/actions.py`
- Create: `safeloop/credentials.py`
- Create: `safeloop/feedback.py`
- Create: `safeloop/state_machine.py`
- Create: `safeloop/web.py`
- Create: `safeloop/demo.py`
- Create: `safeloop/llm/base.py`
- Create: `safeloop/llm/mock.py`
- Create: `safeloop/llm/deepseek.py`
- Create: `safeloop/tools/base.py`
- Create: `safeloop/tools/dispatcher.py`
- Create: `safeloop/tools/files.py`
- Create: `safeloop/tools/commands.py`
- Create: `safeloop/tools/memory.py`
- Create: `safeloop/tools/finish.py`
- Create: `safeloop/security/guardrails.py`
- Create: `safeloop/security/redaction.py`

### Tests and Samples

- Create: `tests/test_cli_bootstrap.py`
- Create: `tests/test_config.py`
- Create: `tests/test_models_events.py`
- Create: `tests/test_llm_actions.py`
- Create: `tests/test_guardrails.py`
- Create: `tests/test_file_tools.py`
- Create: `tests/test_command_tools.py`
- Create: `tests/test_dispatcher.py`
- Create: `tests/test_feedback.py`
- Create: `tests/test_memory.py`
- Create: `tests/test_state_machine.py`
- Create: `tests/test_credentials.py`
- Create: `tests/test_deepseek_client.py`
- Create: `tests/test_web.py`
- Create: `tests/test_demo.py`
- Create: `tests/test_distribution_files.py`
- Create: `samples/python_buggy_calculator/calculator.py`
- Create: `samples/python_buggy_calculator/test_calculator.py`
- Create: `samples/python_buggy_calculator/safeloop.yml`

---

## Dependencies and Parallel Work

### Task Dependency Graph

```text
Task 1 Bootstrap
  -> Task 2 Models + Config
      -> Task 3 Event Log + Run Manager
      -> Task 4 LLM Abstraction + Action Parser
      -> Task 5 Guardrails + Redaction
      -> Task 6 File Tools
      -> Task 7 Command/Test Tools
      -> Task 10 Memory Store
Task 4 + Task 5 + Task 6 + Task 7
  -> Task 8 Tool Dispatcher
Task 7
  -> Task 9 Feedback Classifier
Task 2
  -> Task 10 Memory Store
Task 3 + Task 4 + Task 5 + Task 8 + Task 9 + Task 10
  -> Task 11 State Machine
Task 11
  -> Task 12 CLI + Demo
  -> Task 13 FastAPI WebUI
Task 2 + Task 4
  -> Task 14 Credentials + DeepSeek Client
Task 12 + Task 13 + Task 14
  -> Task 15 CI + Docker + README
Task 15
  -> Task 16 Final Process Docs and Acceptance Evidence
```

### Worktree and PR Plan

- PR 1 / worktree `feature/bootstrap-config`: Task 1、Task 2、Task 3。
- PR 2 / worktree `feature/llm-guardrails`: Task 4、Task 5、Task 14 中 DeepSeek client 的非网络测试。
- PR 3 / worktree `feature/tools-dispatcher`: Task 6、Task 7、Task 8。
- PR 4 / worktree `feature/feedback-memory-loop`: Task 9、Task 10、Task 11。
- PR 5 / worktree `feature/cli-web-demo`: Task 12、Task 13。
- PR 6 / worktree `feature/distribution-docs`: Task 15、Task 16。

### Parallelizable Tasks

- Task 5 Guardrails、Task 6 File Tools、Task 7 Command Tools 可在 Task 2 后并行。
- Task 9 Feedback 可在 Task 7 后独立推进。
- Task 10 Memory 可在 Task 2 后独立推进。
- Task 13 WebUI 可在 Task 11 的接口稳定后与 Task 12 CLI 并行。
- Task 15 Distribution 可在 Task 12 和 Task 13 基本可运行后开始。

---

## Tasks

### Task 1: Repository and Package Bootstrap

**Goal:** 建立可测试的 Python 包骨架、项目命令和基础文档，使后续 task 有稳定入口。

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.gitignore`
- Create: `safeloop/__init__.py`
- Create: `safeloop/__main__.py`
- Create: `safeloop/cli.py`
- Create: `tests/test_cli_bootstrap.py`
- Create: `AGENT_LOG.md`
- Modify: `PLAN.md`

**Interfaces:**
- Produces: `safeloop.__version__: str`
- Produces: `safeloop.cli.main(argv: list[str] | None = None) -> int`
- Produces: `python -m safeloop --help`
- Produces: `make test`

**Expected Implementation:**
- `pyproject.toml` 使用 package name `safeloop-agent`，Python floor 为 `>=3.11`。
- `pyproject.toml` 的 `[build-system]` 必须明确写为 `requires = ["setuptools>=68.0"]` 和 `build-backend = "setuptools.build_meta"`。
- Runtime dependencies: `fastapi`, `uvicorn`, `pydantic`, `pyyaml`, `httpx`, `keyring`, `python-dotenv`。
- Dev dependencies: `pytest`, `pytest-cov`。
- CLI 使用标准库 `argparse`，先提供 `--version`、`--help`、`demo`、`web`、`credentials`、`run` 子命令占位入口；未实现的占位子命令返回 exit code `1` 并打印包含 `not yet implemented` 的信息，不执行 agent。
- `.gitignore` 必须包含 `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.safeloop/`, `dist/`, `build/`。

- [x] **Step 1: Write the failing test**

```python
# tests/test_cli_bootstrap.py
import subprocess
import sys


def test_module_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "SafeLoop Coding Agent Harness" in result.stdout
    assert "demo" in result.stdout
    assert "web" in result.stdout


def test_version_flag_prints_version():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "--version"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip().startswith("safeloop ")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_bootstrap.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'safeloop'`.

- [x] **Step 3: Write minimal implementation**

Create the package files and CLI entry with the interfaces listed above. `main()` must return an integer exit code. `__main__.py` must call `raise SystemExit(main())`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_bootstrap.py -v`

Expected: PASS for both tests.

- [x] **Step 5: Verify one-command test target**

Run: `make test`

If `make` is unavailable on Windows, run: `python -m pytest`

Expected: Runs the pytest suite and exits 0.

- [x] **Step 6: Commit and log**

```bash
git add pyproject.toml Makefile .gitignore safeloop tests AGENT_LOG.md PLAN.md
git commit -m "chore(task-1): bootstrap safeloop package"
```

Implementation commit: `db94d5c` (`test(task-1): cover placeholder cli commands`).

Updated `AGENT_LOG.md` with the Task 1 entry for implementation subagent `Mendel` and reviewer/fix loop.

---

### Task 2: Core Data Models and Config Loader

**Goal:** 定义 harness 的核心数据模型和配置加载规则，为所有后续机制提供稳定类型。

**Files:**
- Create: `safeloop/models.py`
- Create: `safeloop/config.py`
- Create: `tests/test_config.py`
- Create: `tests/test_models_events.py`
- Modify: `pyproject.toml`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `safeloop.__version__`
- Produces: `class HarnessConfig(BaseModel)`
- Produces: `class RunRecord(BaseModel)`
- Produces: `class AgentAction(BaseModel)`
- Produces: `class ToolResult(BaseModel)`
- Produces: `class GuardrailDecision(BaseModel)`
- Produces: `class Feedback(BaseModel)`
- Produces: `class MemoryEntry(BaseModel)`
- Produces: `class Event(BaseModel)`
- Produces: `load_config(path: Path | str) -> HarnessConfig`
- Produces: `resolve_workspace(path: Path | str) -> Path`

**Expected Implementation:**
- 使用 Pydantic model，枚举字段使用 `Literal`。
- `HarnessConfig` 字段包括 `workspace`, `allowed_paths`, `blocked_paths`, `test_command`, `lint_command`, `build_command`, `blocked_commands`, `approval_required_commands`, `llm_provider`, `model`, `credential_backend`, `max_steps`, `command_timeout_seconds`, `max_file_bytes`。
- 默认值：`llm_provider="mock"`, `credential_backend="keyring"`, `max_steps=10`, `command_timeout_seconds=60`, `max_file_bytes=200_000`。
- `load_config()` 读取 YAML，校验 workspace 存在，路径相对 workspace 解析。
- 配置错误抛出 `ConfigError`，错误信息包含字段名。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_config.py
from pathlib import Path

import pytest

from safeloop.config import ConfigError, load_config


def test_load_config_applies_defaults(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {workspace}\n"
        "test_command: python -m pytest\n"
        "allowed_paths:\n"
        "  - .\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.workspace == workspace.resolve()
    assert config.llm_provider == "mock"
    assert config.credential_backend == "keyring"
    assert config.max_steps == 10
    assert config.command_timeout_seconds == 60
    assert config.max_file_bytes == 200_000


def test_load_config_rejects_missing_workspace(tmp_path: Path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        "workspace: missing\n"
        "test_command: python -m pytest\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="workspace"):
        load_config(config_path)
```

```python
# tests/test_models_events.py
from safeloop.models import AgentAction, GuardrailDecision, ToolResult


def test_agent_action_requires_registered_shape():
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": "app.py"},
        reason="inspect target file",
        expected_outcome="source content",
    )

    assert action.tool_name == "read_file"
    assert action.arguments["path"] == "app.py"


def test_tool_result_limits_basic_fields():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="",
        stderr="E   AssertionError",
        summary="tests failed",
        duration_ms=12,
    )

    assert result.success is False
    assert result.exit_code == 1


def test_guardrail_decision_uses_known_values():
    decision = GuardrailDecision(
        decision="deny",
        risk_level="critical",
        reason="dangerous command",
        matched_rule="blocked_commands",
    )

    assert decision.decision == "deny"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py tests/test_models_events.py -v`

Expected: FAIL with import errors for `safeloop.config` or missing model classes.

- [x] **Step 3: Write minimal implementation**

Create Pydantic models and config loader matching the interfaces. Do not add LLM, tool, or state machine logic in this task.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_config.py tests/test_models_events.py -v`

Expected: PASS.

- [x] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [x] **Step 6: Commit and log**

```bash
git add safeloop/models.py safeloop/config.py tests/test_config.py tests/test_models_events.py pyproject.toml PLAN.md AGENT_LOG.md
git commit -m "feat(task-2): add core models and config loader"
```

Implementation commit: `2699c02` (`fix(task-2): remove toolresult metadata`).

Update `PLAN.md` Task 2 with the commit hash and append an `AGENT_LOG.md` entry.

Review fix commit: `e3b1377` (`fix(task-2): resolve run workspace paths`).

PR1 review fix commit: `fbca894` (`fix(pr1): tighten config workspace boundaries`) rejects `allowed_paths`/`blocked_paths` that escape `workspace`, rejects file-backed `workspace` values, and preserves the explicit review trail in `AGENT_LOG.md`.

PR1 review follow-up commit: `1cd198c` (`fix(pr1): validate redaction env var names`) ensures `redaction_secret_env_vars` stores environment variable names only, not secret-like or malformed values.

---

### Task 3: Event Log Store and Run Manager

**Goal:** 记录 run、状态变化和事件，为 CLI、WebUI、测试和审计提供统一数据源。

**Files:**
- Create: `safeloop/events.py`
- Create: `safeloop/run_manager.py`
- Create: `safeloop/security/redaction.py`
- Create: `tests/test_models_events.py`
- Modify: `safeloop/models.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `RunRecord`, `Event`, `HarnessConfig`
- Produces: `redact_secrets(value: object, known_secrets: list[str] | None = None) -> object`
- Produces: `class EventLogStore`
- Produces: `EventLogStore.append(event: Event) -> Event`
- Produces: `EventLogStore.list(run_id: str) -> list[Event]`
- Produces: `class RunManager`
- Produces: `RunManager.create_run(task: str, config: HarnessConfig) -> RunRecord`
- Produces: `RunManager.update_status(run_id: str, status: str, reason: str | None = None) -> RunRecord`
- Produces: `RunManager.get_run(run_id: str) -> RunRecord`

**Expected Implementation:**
- 第一版使用进程内存存储，事件 payload 写入前脱敏。
- `RunManager.create_run()` 生成 UUID 字符串，初始 status 为 `created`。
- `update_status()` 写入 `state_changed` 事件。
- 缺失 run 抛出 `RunNotFoundError`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_models_events.py
from pathlib import Path

import pytest

from safeloop.config import HarnessConfig
from safeloop.events import EventLogStore
from safeloop.models import Event
from safeloop.run_manager import RunManager, RunNotFoundError
from safeloop.security.redaction import redact_secrets


def make_config(workspace: Path) -> HarnessConfig:
    return HarnessConfig(workspace=workspace, test_command="python -m pytest")


def test_redaction_removes_known_secret():
    payload = {"message": "token sk-secret appears", "nested": {"key": "sk-secret"}}

    redacted = redact_secrets(payload, known_secrets=["sk-secret"])

    assert "sk-secret" not in str(redacted)
    assert "[REDACTED]" in str(redacted)


def test_run_manager_creates_run_and_state_event(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)

    run = manager.create_run("fix failing test", make_config(tmp_path))
    manager.update_status(run.id, "running", reason="agent started")

    events = store.list(run.id)
    assert run.status == "created"
    assert manager.get_run(run.id).status == "running"
    assert [event.type for event in events] == ["run_created", "state_changed"]


def test_run_manager_missing_run_raises():
    manager = RunManager(event_store=EventLogStore())

    with pytest.raises(RunNotFoundError, match="missing"):
        manager.get_run("missing")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_models_events.py -v`

Expected: FAIL with import errors for `EventLogStore`, `RunManager`, or `redact_secrets`.

- [x] **Step 3: Write minimal implementation**

Implement in-memory event and run stores. Ensure all event payloads pass through `redact_secrets()`.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_models_events.py -v`

Expected: PASS.

- [x] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [x] **Step 6: Commit and log**

```bash
git add safeloop/events.py safeloop/run_manager.py safeloop/security/redaction.py safeloop/models.py tests/test_models_events.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-3): add event log and run manager"
```

Implementation commit: `8ef8c28` (`feat(task-3): add event log and run manager`), completed by subagent Dalton.

Review fix commit: `b303d1f` (`fix(task-3): isolate event log copies`), completed by subagent Rawls after reviewer Feynman flagged mutable event-history exposure.

Review fix commit: `88f4537` (`fix(task-3): strengthen event redaction traceability`), completed by subagent Zeno after reviewer findings required configured known-secret redaction, stronger key/content heuristics, UUID-shape coverage, and explicit Task 3 traceability notes.

Review fix commit: `f5aad67` (`fix(task-3): wire runtime redaction secrets`), completed by subagent Fermat to add config-owned secret env var names, deterministic runtime secret collection, and default `RunManager()` wiring so Task 3 events redact configured runtime secret values without storing secrets in config.

PR1 review fix commit: `fbca894` (`fix(pr1): tighten config workspace boundaries`) also closes the branch-level Minor by making dotenv-style secret-line redaction case-insensitive for lowercase assignments such as `api_key=...`.

PR1 review follow-up commit: `1cd198c` (`fix(pr1): validate redaction env var names`) keeps runtime redaction configuration name-only by rejecting secret-like values in `redaction_secret_env_vars`.

Update `PLAN.md` Task 3 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 4: LLM Abstraction and Action Parser

**Status:** DONE in commit `c107cae` (`feat(task-4): add llm abstraction and action parser`) by implementer subagent Turing.

**Goal:** 将真实 LLM 的不确定性隔离在可替换接口后面，并把模型输出解析成可验证的结构化动作。

**Files:**
- Create: `safeloop/llm/base.py`
- Create: `safeloop/llm/mock.py`
- Create: `safeloop/actions.py`
- Create: `tests/test_llm_actions.py`
- Modify: `safeloop/models.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `AgentAction`, `Feedback`, `MemoryEntry`
- Produces: `class LLMClient(Protocol)`
- Produces: `class LLMRequest(BaseModel)`
- Produces: `class MockLLMClient`
- Produces: `MockLLMClient.complete(request: LLMRequest) -> str`
- Produces: `parse_action(raw: str, allowed_tools: set[str]) -> AgentAction`
- Produces: `ActionParseError`

**Expected Implementation:**
- `MockLLMClient` 接收脚本化响应列表，按顺序返回 JSON 字符串。
- `parse_action()` 只接受 JSON object，必须包含 `tool_name`, `arguments`, `reason`, `expected_outcome`。
- 未知工具、非法 JSON、缺失字段都抛出 `ActionParseError`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_llm_actions.py
import pytest

from safeloop.actions import ActionParseError, parse_action
from safeloop.llm.base import LLMRequest
from safeloop.llm.mock import MockLLMClient


def test_mock_llm_returns_scripted_actions():
    client = MockLLMClient(
        responses=[
            '{"tool_name":"read_file","arguments":{"path":"app.py"},"reason":"inspect","expected_outcome":"content"}'
        ]
    )

    raw = client.complete(LLMRequest(task="fix", feedback=[], memories=[], events=[]))

    assert '"read_file"' in raw


def test_parse_action_accepts_known_tool():
    action = parse_action(
        '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
        allowed_tools={"run_tests"},
    )

    assert action.tool_name == "run_tests"
    assert action.reason == "verify"


def test_parse_action_rejects_unknown_tool():
    with pytest.raises(ActionParseError, match="unknown tool"):
        parse_action(
            '{"tool_name":"delete_database","arguments":{},"reason":"bad","expected_outcome":"gone"}',
            allowed_tools={"read_file"},
        )


def test_parse_action_rejects_invalid_json():
    with pytest.raises(ActionParseError, match="valid JSON"):
        parse_action("not json", allowed_tools={"read_file"})
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_llm_actions.py -v`

Expected: FAIL with missing `safeloop.actions` or parser symbols.

- [x] **Step 3: Write minimal implementation**

Create the LLM protocol, request model, mock client, and parser. Do not call DeepSeek in this task.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_llm_actions.py -v`

Expected: PASS.

- [x] **Step 5: Run full tests**

Run: `python -m pytest -v`

Expected: PASS.

- [x] **Step 6: Commit and log**

```bash
git add safeloop/llm safeloop/actions.py safeloop/models.py tests/test_llm_actions.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-4): add llm abstraction and action parser"
```

Update `PLAN.md` Task 4 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 5: Guardrails and Secret Redaction

**Goal:** 用确定性代码拦截 workspace 外路径、敏感文件和危险命令，落实 A 项“危险动作必须是代码机制”的要求。

**Files:**
- Create: `safeloop/security/guardrails.py`
- Modify: `safeloop/security/redaction.py`
- Create: `tests/test_guardrails.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `AgentAction`, `HarnessConfig`, `GuardrailDecision`
- Produces: `class GuardrailEngine`
- Produces: `GuardrailEngine.evaluate(action: AgentAction) -> GuardrailDecision`
- Produces: `is_path_within_workspace(workspace: Path, candidate: Path) -> bool`
- Produces: `GuardrailError`

**Expected Implementation:**
- 默认阻止文件名或路径片段：`.env`, `id_rsa`, `id_ed25519`, `.ssh`, `.git/config`, `history`。
- 默认阻止命令模式：`rm -rf /`, `git push`, `docker push`, `kubectl delete`, `drop database`, `shutdown`, `reboot`。
- 访问 workspace 外路径必须 `deny`。
- 命中 `approval_required_commands` 返回 `require_approval`。
- 规则冲突时选择更安全决策：`deny` 优先于 `require_approval`，`require_approval` 优先于 `allow`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_guardrails.py
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction
from safeloop.security.guardrails import GuardrailEngine, is_path_within_workspace


def make_config(workspace: Path) -> HarnessConfig:
    return HarnessConfig(
        workspace=workspace,
        test_command="python -m pytest",
        allowed_paths=["."],
        approval_required_commands=["pip install"],
    )


def test_path_outside_workspace_is_blocked(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    assert is_path_within_workspace(workspace, workspace / "app.py") is True
    assert is_path_within_workspace(workspace, outside) is False


def test_guardrail_denies_env_file(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": ".env"},
        reason="inspect",
        expected_outcome="content",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert decision.risk_level in {"high", "critical"}


def test_guardrail_denies_dangerous_command(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="run_command",
        arguments={"command": "rm -rf /"},
        reason="clean",
        expected_outcome="cleaned",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "deny"
    assert "blocked" in decision.matched_rule


def test_guardrail_requires_approval_for_configured_command(tmp_path: Path):
    engine = GuardrailEngine(make_config(tmp_path))
    action = AgentAction(
        tool_name="run_command",
        arguments={"command": "pip install requests"},
        reason="install dependency",
        expected_outcome="installed",
    )

    decision = engine.evaluate(action)

    assert decision.decision == "require_approval"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_guardrails.py -v`

Expected: FAIL with missing `GuardrailEngine`.

- [x] **Step 3: Write minimal implementation**

Implement deterministic path and command checks. Do not execute commands or read files inside guardrails.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_guardrails.py -v`

Expected: PASS.

- [x] **Step 5: Run full tests**

Run: `python -m pytest -v`

Expected: PASS.

- [x] **Step 6: Commit and log**

```bash
git add safeloop/security/guardrails.py safeloop/security/redaction.py tests/test_guardrails.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-5): add deterministic guardrails"
```

Update `PLAN.md` Task 5 with the commit hash and append an `AGENT_LOG.md` entry.

Task 5 implementation commit: `92c7022` (`feat(task-5): add deterministic guardrails`).

Task 5 review-fix commit: `5a48883` (`fix(task-5): guard generic action arguments`).

---

### Task 6: Workspace-Bounded File Tools

**Goal:** 实现 list/read/write/patch 文件工具，并保证路径逃逸、敏感文件、过大文件和二进制文件被安全处理。

**Files:**
- Create: `safeloop/tools/base.py`
- Create: `safeloop/tools/files.py`
- Create: `tests/test_file_tools.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `HarnessConfig`, `ToolResult`
- Produces: `class ToolContext(BaseModel)`
- Produces: `class FileTools`
- Produces: `FileTools.list_files(path: str = ".") -> ToolResult`
- Produces: `FileTools.read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> ToolResult`
- Produces: `FileTools.write_file(path: str, content: str) -> ToolResult`
- Produces: `FileTools.patch_file(path: str, old: str, new: str) -> ToolResult`
- Produces: `FileToolError`

**Expected Implementation:**
- 所有文件路径先相对 workspace 解析，再调用 guardrail/path check。
- `read_file()` 超过 `max_file_bytes` 返回失败 `ToolResult`，不读取完整内容。
- `patch_file()` 要求 `old` 在文件中出现一次且仅一次；否则返回失败，不写入。
- `list_files()` 不列出 `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.safeloop`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_file_tools.py
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.tools.base import ToolContext
from safeloop.tools.files import FileTools


def make_tools(workspace: Path, max_file_bytes: int = 200_000) -> FileTools:
    config = HarnessConfig(
        workspace=workspace,
        test_command="python -m pytest",
        max_file_bytes=max_file_bytes,
    )
    return FileTools(ToolContext(config=config, run_id="run-1", step=1))


def test_read_file_inside_workspace(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("app.py")

    assert result.success is True
    assert "print" in result.stdout


def test_read_file_rejects_workspace_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("../outside-secret.txt")

    assert result.success is False
    assert "outside workspace" in result.summary


def test_patch_file_replaces_unique_text(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.patch_file("app.py", old="value = 1", new="value = 2")

    assert result.success is True
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "value = 2\n"


def test_patch_file_rejects_ambiguous_match(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("x = 1\nx = 1\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.patch_file("app.py", old="x = 1", new="x = 2")

    assert result.success is False
    assert path.read_text(encoding="utf-8") == "x = 1\nx = 1\n"


def test_read_file_rejects_too_large_file(tmp_path: Path):
    (tmp_path / "large.txt").write_text("abcdef", encoding="utf-8")
    tools = make_tools(tmp_path, max_file_bytes=3)

    result = tools.read_file("large.txt")

    assert result.success is False
    assert "too large" in result.summary
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_file_tools.py -v`

Observed RED:

```text
ModuleNotFoundError: No module named 'safeloop.tools'
```

- [x] **Step 3: Write minimal implementation**

Implement `ToolContext` and file operations. Reuse path boundary checks from Task 5.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_file_tools.py -v`

Observed GREEN: `11 passed in 0.49s`

- [x] **Step 5: Run full tests**

Run: `make test`

Windows fallback used here:

```bash
python -m pytest -v
```

Observed GREEN: `78 passed in 3.89s`

- [x] **Step 6: Commit and log**

```bash
git add safeloop/tools/base.py safeloop/tools/files.py tests/test_file_tools.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-6): add workspace bounded file tools"
```

Implementation commit: `54c806d` (`feat(task-6): add workspace bounded file tools`).

Updated `PLAN.md` Task 6 with the implementation hash and appended the Task 6 `AGENT_LOG.md` entry.

Review-fix commit: `a02f636` (`fix(task-6): keep allowed dot directories visible`).
The review fix narrowed `list_files()` to exclude only `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and `.safeloop`, while the new regression coverage proved `.github` stays visible and `patch_file()` still rejects zero-match edits without changing file contents.

---

### Task 7: Command and Test Tools

**Status:** DONE in commit `08e849a` (`feat(task-7): add command and test tools`). Implementer subagent Lovelace wrote the tests and implementation; controller completed verification, process documentation, and commit after the subagent timed out before reporting.

**Goal:** 在 workspace 内执行允许的命令和测试命令，收集 exit code、stdout、stderr、耗时和超时结果。

**Files:**
- Create: `safeloop/tools/commands.py`
- Create: `tests/test_command_tools.py`
- Modify: `safeloop/tools/base.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `ToolContext`, `ToolResult`, `HarnessConfig`
- Produces: `class CommandTools`
- Produces: `CommandTools.run_command(command: str, timeout_seconds: int | None = None) -> ToolResult`
- Produces: `CommandTools.run_tests() -> ToolResult`
- Produces: `CommandToolError`

**Expected Implementation:**
- 使用 `subprocess.run(..., cwd=config.workspace, shell=True, text=True, capture_output=True, timeout=...)`。
- 命令执行前必须调用 `GuardrailEngine.evaluate()`。
- 命令输出进入 `ToolResult` 前截断到可配置长度，默认每个 stream 4000 字符。
- timeout 返回 `success=False`, `summary` 包含 `timeout`。
- `run_tests()` 使用 `config.test_command`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_command_tools.py
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.tools.base import ToolContext
from safeloop.tools.commands import CommandTools


def make_tools(workspace: Path, command_timeout_seconds: int = 60) -> CommandTools:
    config = HarnessConfig(
        workspace=workspace,
        test_command="python -c \"print('tests ok')\"",
        command_timeout_seconds=command_timeout_seconds,
    )
    return CommandTools(ToolContext(config=config, run_id="run-1", step=1))


def test_run_command_captures_stdout(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command("python -c \"print('hello')\"")

    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_run_command_blocks_dangerous_command(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_command("rm -rf /")

    assert result.success is False
    assert "guardrail" in result.summary.lower()


def test_run_tests_uses_configured_command(tmp_path: Path):
    tools = make_tools(tmp_path)

    result = tools.run_tests()

    assert result.success is True
    assert "tests ok" in result.stdout


def test_run_command_reports_timeout(tmp_path: Path):
    tools = make_tools(tmp_path, command_timeout_seconds=1)

    result = tools.run_command(
        "python -c \"import time; time.sleep(2)\"",
        timeout_seconds=1,
    )

    assert result.success is False
    assert "timeout" in result.summary.lower()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_command_tools.py -v`

Expected: FAIL with missing `CommandTools`.

Observed RED:

```text
ModuleNotFoundError: No module named 'safeloop.tools.commands'
```

- [x] **Step 3: Write minimal implementation**

Implement command execution with guardrail checks, timeout handling, output truncation and standardized `ToolResult`.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_command_tools.py -v`

Expected: PASS.

Observed GREEN: `7 passed in 3.26s`

- [x] **Step 5: Run full tests**

Run: `python -m pytest -v`

Observed GREEN: `86 passed in 6.75s`

- [x] **Step 6: Commit and log**

```bash
git add safeloop/tools/commands.py safeloop/tools/base.py tests/test_command_tools.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-7): add command and test tools"
```

Update `PLAN.md` Task 7 with the commit hash and append an `AGENT_LOG.md` entry.

**Branch Review Fix:** reviewer Hooke found that command guardrails could be bypassed by extra whitespace and that `OSError` escaped as `CommandToolError` instead of a structured `ToolResult`. RED tests `test_guardrail_normalizes_command_whitespace_before_matching`, `test_run_command_blocks_whitespace_variant_without_execution`, and `test_run_command_returns_structured_result_for_oserror` failed first; GREEN focused verification `python -m pytest tests/test_guardrails.py tests/test_command_tools.py -v` = `19 passed`; full verification `python -m pytest -v` = `103 passed`. Commit: `f58d2f5`.

---

### Task 8: Tool Dispatcher and Tool Registry

**Goal:** 用统一 dispatcher 注册、校验和调用所有工具，落实主要贡献“工具分发与执行状态机设计”的工具分发部分。

**Status:** completed in commit `4c43dbd`; review fix added in commit `e631cc3`; focused dispatcher tests `13 passed`, full suite `100 passed`.

**Files:**
- Create: `safeloop/tools/dispatcher.py`
- Create: `safeloop/tools/memory.py`
- Create: `safeloop/tools/finish.py`
- Create: `tests/test_dispatcher.py`
- Modify: `safeloop/tools/base.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `AgentAction`, `ToolContext`, `ToolResult`, file tools, command tools
- Produces: `class ToolSpec(BaseModel)`
- Produces: `class ToolDispatcher`
- Produces: `ToolDispatcher.available_tools() -> set[str]`
- Produces: `ToolDispatcher.dispatch(action: AgentAction) -> ToolResult`
- Produces: `ToolDispatcher.tool_schemas() -> list[dict[str, object]]`
- Produces: `UnknownToolError`

**Expected Implementation:**
- 注册工具：`list_files`, `read_file`, `write_file`, `patch_file`, `run_command`, `run_tests`, `save_memory`, `load_memory`, `finish`。
- 参数缺失或类型错误返回失败 `ToolResult`，不抛出未捕获异常。
- `finish` 返回 `ToolResult(success=True, summary="finished")`，并在 metadata 中标记 `finish=True`。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dispatcher.py
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.models import AgentAction
from safeloop.tools.base import ToolContext
from safeloop.tools.dispatcher import ToolDispatcher


def make_dispatcher(workspace: Path) -> ToolDispatcher:
    config = HarnessConfig(
        workspace=workspace,
        test_command="python -c \"print('ok')\"",
    )
    return ToolDispatcher(ToolContext(config=config, run_id="run-1", step=1))


def test_dispatcher_lists_required_tools(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)

    assert {
        "list_files",
        "read_file",
        "patch_file",
        "run_command",
        "run_tests",
        "save_memory",
        "load_memory",
        "finish",
    }.issubset(dispatcher.available_tools())


def test_dispatcher_routes_read_file(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    dispatcher = make_dispatcher(tmp_path)
    action = AgentAction(
        tool_name="read_file",
        arguments={"path": "app.py"},
        reason="inspect",
        expected_outcome="content",
    )

    result = dispatcher.dispatch(action)

    assert result.success is True
    assert "x = 1" in result.stdout


def test_dispatcher_rejects_unknown_tool(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)
    action = AgentAction(
        tool_name="unknown",
        arguments={},
        reason="bad",
        expected_outcome="none",
    )

    result = dispatcher.dispatch(action)

    assert result.success is False
    assert "unknown tool" in result.summary.lower()


def test_dispatcher_finish_sets_metadata(tmp_path: Path):
    dispatcher = make_dispatcher(tmp_path)
    action = AgentAction(
        tool_name="finish",
        arguments={"message": "done"},
        reason="complete",
        expected_outcome="stop",
    )

    result = dispatcher.dispatch(action)

    assert result.success is True
    assert result.metadata["finish"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dispatcher.py -v`

Expected: FAIL with missing `ToolDispatcher`.

- [ ] **Step 3: Write minimal implementation**

Implement registry, dispatch routing and finish tool. Register `save_memory` and `load_memory` tool names in this task; before Task 10 adds persistence, those two tools return `ToolResult(success=False, summary="memory store unavailable")` so callers receive structured results.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_dispatcher.py -v`

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 6: Commit and log**

```bash
git add safeloop/tools/dispatcher.py safeloop/tools/memory.py safeloop/tools/finish.py safeloop/tools/base.py tests/test_dispatcher.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-8): add tool dispatcher"
```

Update `PLAN.md` Task 8 with the commit hash and append an `AGENT_LOG.md` entry.

**Task 8 Evidence:** RED regression `test_memory_tools_report_unavailable_without_arguments` failed because `save_memory` reported missing `content`; GREEN focused verification `python -m pytest tests/test_dispatcher.py -v` = `12 passed`; full verification `python -m pytest -v` = `99 passed`. Reviewer Hubble found one Important process issue, corrected in review-fix commit `e631cc3`; final focused verification `python -m pytest tests/test_dispatcher.py -v` = `13 passed`; final full verification `python -m pytest -v` = `100 passed`. Implementation commit: `4c43dbd`.

---

### Task 9: Feedback Classifier

**Status:** implemented locally; focused feedback tests `7 passed`, full suite `110 passed`; commit hash pending.

**Goal:** 把工具输出、测试失败、超时、护栏拦截和解析错误转成下一轮 LLM 可消费的压缩反馈。

**Files:**
- Create: `safeloop/feedback.py`
- Create: `tests/test_feedback.py`
- Modify: `safeloop/models.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `ToolResult`, `GuardrailDecision`
- Produces: `class FeedbackClassifier`
- Produces: `FeedbackClassifier.from_tool_result(result: ToolResult) -> Feedback`
- Produces: `FeedbackClassifier.from_parse_error(message: str) -> Feedback`
- Produces: `FeedbackClassifier.from_guardrail(decision: GuardrailDecision) -> Feedback`

**Expected Implementation:**
- exit code 非 0 且 stderr/stdout 包含 `AssertionError` 或 `FAILED` 时分类为 `test_failure`。
- summary 包含 `SyntaxError` 时分类为 `syntax_error`。
- summary 包含 `timeout` 时分类为 `timeout`。
- guardrail deny 分类为 `guardrail_blocked`。
- 原始片段最长 1200 字符，并经过 redaction。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_feedback.py
from safeloop.feedback import FeedbackClassifier
from safeloop.models import GuardrailDecision, ToolResult


def test_classifier_detects_test_failure():
    result = ToolResult(
        tool_name="run_tests",
        success=False,
        exit_code=1,
        stdout="FAILED test_app.py::test_add - AssertionError",
        stderr="",
        summary="tests failed",
        duration_ms=20,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert feedback.kind == "test_failure"
    assert "AssertionError" in feedback.raw_excerpt


def test_classifier_detects_timeout():
    result = ToolResult(
        tool_name="run_command",
        success=False,
        exit_code=None,
        stdout="",
        stderr="",
        summary="command timeout after 1s",
        duration_ms=1000,
    )

    feedback = FeedbackClassifier().from_tool_result(result)

    assert feedback.kind == "timeout"


def test_classifier_redacts_secret_excerpt():
    result = ToolResult(
        tool_name="run_command",
        success=False,
        exit_code=1,
        stdout="secret sk-example-token",
        stderr="",
        summary="failed",
        duration_ms=1,
    )

    feedback = FeedbackClassifier(known_secrets=["sk-example-token"]).from_tool_result(result)

    assert "sk-example-token" not in feedback.raw_excerpt


def test_classifier_converts_guardrail_block():
    decision = GuardrailDecision(
        decision="deny",
        risk_level="critical",
        reason="dangerous command",
        matched_rule="blocked_commands",
    )

    feedback = FeedbackClassifier().from_guardrail(decision)

    assert feedback.kind == "guardrail_blocked"
    assert "dangerous command" in feedback.summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_feedback.py -v`

Expected: FAIL with missing `FeedbackClassifier`.

- [ ] **Step 3: Write minimal implementation**

Implement deterministic classification rules and output truncation.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_feedback.py -v`

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 6: Commit and log**

```bash
git add safeloop/feedback.py safeloop/models.py tests/test_feedback.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-9): add feedback classifier"
```

Update `PLAN.md` Task 9 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 10: Project Memory Store

**Goal:** 实现项目级记忆的保存、读取、标签过滤和 secret 防护，使 agent 能跨 run 使用项目规则。

**Files:**
- Create: `safeloop/tools/memory.py`
- Create: `tests/test_memory.py`
- Modify: `safeloop/models.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `MemoryEntry`, `ToolContext`
- Produces: `class MemoryStore`
- Produces: `MemoryStore.save(scope: str, tags: list[str], content: str, source_run_id: str | None = None) -> MemoryEntry`
- Produces: `MemoryStore.query(scope: str | None = None, tags: list[str] | None = None) -> list[MemoryEntry]`
- Produces: `MemoryStore.load_all() -> list[MemoryEntry]`
- Produces: `MemoryStore.clear() -> None`

**Expected Implementation:**
- 默认存储路径为 `<workspace>/.safeloop/memory.json`。
- JSON 文件不存在时返回空列表。
- 保存前调用 redaction，拒绝明显 secret 内容。
- 查询支持 scope 和 tag 交集过滤。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory.py
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
        store.save(scope="project", tags=["key"], content="DEEPSEEK_API_KEY=sk-secret")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_memory.py -v`

Expected: FAIL with missing `MemoryStore`.

- [ ] **Step 3: Write minimal implementation**

Implement JSON persistence, directory creation, redaction and tag filtering.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_memory.py -v`

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 6: Commit and log**

```bash
git add safeloop/tools/memory.py tests/test_memory.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-10): add project memory store"
```

Update `PLAN.md` Task 10 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 11: Agent State Machine Loop

**Goal:** 实现核心 agent loop：context -> LLM action -> parse -> guard -> dispatch -> observe -> feedback -> stop/continue。

**Files:**
- Create: `safeloop/state_machine.py`
- Create: `tests/test_state_machine.py`
- Modify: `safeloop/run_manager.py`
- Modify: `safeloop/events.py`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `RunManager`, `EventLogStore`, `LLMClient`, `ToolDispatcher`, `GuardrailEngine`, `FeedbackClassifier`, `MemoryStore`
- Produces: `class AgentStateMachine`
- Produces: `AgentStateMachine.run(task: str, config: HarnessConfig) -> RunRecord`
- Produces: `class StopReason`
- Produces Event types: `run_created`, `state_changed`, `llm_action`, `guardrail_decision`, `tool_result`, `feedback_added`, `finished`, `stopped`

**Expected Implementation:**
- 状态流转：`INIT -> CONTEXT -> DECIDE -> GUARD -> DISPATCH -> OBSERVE -> FEEDBACK -> FINISH/STOP`。
- 每轮调用 LLM 前构造 `LLMRequest`，包含任务、反馈、记忆、事件摘要和工具 schema。
- `finish` 工具或 `ToolResult.metadata["finish"] is True` 时状态变为 `finished`。
- 达到 `max_steps` 时状态变为 `stopped`，停止原因包含 `max_steps`。
- parse error 进入 feedback；连续 parse error 达到 2 次时停止。
- guardrail deny 不执行工具，转成反馈并继续下一轮；如果下一轮仍危险，可在 max_steps 前持续记录。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state_machine.py
from pathlib import Path

from safeloop.config import HarnessConfig
from safeloop.events import EventLogStore
from safeloop.llm.mock import MockLLMClient
from safeloop.run_manager import RunManager
from safeloop.state_machine import AgentStateMachine


def make_config(workspace: Path, max_steps: int = 10) -> HarnessConfig:
    return HarnessConfig(
        workspace=workspace,
        test_command="python -c \"print('tests pass')\"",
        max_steps=max_steps,
    )


def test_state_machine_finishes_with_mock_llm(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
            '{"tool_name":"finish","arguments":{"message":"done"},"reason":"tests pass","expected_outcome":"stop"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("verify project", make_config(tmp_path))

    assert run.status == "finished"
    assert "llm_action" in [event.type for event in store.list(run.id)]
    assert "tool_result" in [event.type for event in store.list(run.id)]
    assert "finished" in [event.type for event in store.list(run.id)]


def test_state_machine_blocks_dangerous_action_before_dispatch(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_command","arguments":{"command":"rm -rf /"},"reason":"clean","expected_outcome":"clean"}',
            '{"tool_name":"finish","arguments":{"message":"blocked safely"},"reason":"guardrail feedback received","expected_outcome":"stop"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("danger demo", make_config(tmp_path))

    events = store.list(run.id)
    assert run.status == "finished"
    assert any(event.type == "guardrail_decision" and event.payload["decision"] == "deny" for event in events)
    assert not any(event.type == "tool_result" and event.payload.get("command") == "rm -rf /" for event in events)


def test_state_machine_stops_at_max_steps(tmp_path: Path):
    store = EventLogStore()
    manager = RunManager(event_store=store)
    client = MockLLMClient(
        responses=[
            '{"tool_name":"run_tests","arguments":{},"reason":"verify","expected_outcome":"pass"}',
            '{"tool_name":"run_tests","arguments":{},"reason":"verify again","expected_outcome":"pass"}',
        ]
    )
    machine = AgentStateMachine(run_manager=manager, event_store=store, llm_client=client)

    run = machine.run("loop", make_config(tmp_path, max_steps=1))

    assert run.status == "stopped"
    assert any("max_steps" in str(event.payload) for event in store.list(run.id))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_state_machine.py -v`

Expected: FAIL with missing `AgentStateMachine`.

- [ ] **Step 3: Write minimal implementation**

Implement the loop and event sequence using existing modules. Keep the state machine independent from CLI and WebUI.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_state_machine.py -v`

Expected: PASS.

- [ ] **Step 5: Run mechanism-focused tests**

Run: `python -m pytest tests/test_state_machine.py tests/test_guardrails.py tests/test_dispatcher.py tests/test_feedback.py -v`

Expected: PASS.

- [ ] **Step 6: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 7: Commit and log**

```bash
git add safeloop/state_machine.py safeloop/run_manager.py safeloop/events.py tests/test_state_machine.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-11): add agent state machine loop"
```

Update `PLAN.md` Task 11 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 12: CLI Commands and Deterministic Mechanism Demo

**Goal:** 提供用户可运行的 CLI：执行 run、机制演示、凭据状态入口和 WebUI 启动入口；同时提交 mock LLM 机制演示。

**Files:**
- Modify: `safeloop/cli.py`
- Create: `safeloop/demo.py`
- Create: `tests/test_demo.py`
- Modify: `tests/test_cli_bootstrap.py`
- Create: `samples/python_buggy_calculator/calculator.py`
- Create: `samples/python_buggy_calculator/test_calculator.py`
- Create: `samples/python_buggy_calculator/safeloop.yml`
- Modify: `Makefile`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `AgentStateMachine`, `MockLLMClient`, `load_config`
- Produces: `python -m safeloop run --config safeloop.yml --task "..." --llm mock`
- Produces: `python -m safeloop demo`
- Produces: `python -m safeloop credentials status`
- Produces: `make demo`
- Produces: `run_demo() -> int`

**Expected Implementation:**
- `demo` 在 mock LLM 下确定性展示三件事：护栏拦截危险动作、测试失败反馈进入下一轮、下一轮动作改变并最终完成。
- demo 使用 `samples/python_buggy_calculator`，其中初始 `calculator.py` 有一个可被 patch 修复的小 bug。
- CLI 输出 run id、最终状态和关键事件摘要。
- `run` 子命令从配置文件加载 workspace，不要求真实 LLM。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_demo.py
import subprocess
import sys


def test_demo_command_runs_deterministically():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "demo"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "guardrail_blocked" in result.stdout
    assert "feedback_added" in result.stdout
    assert "finished" in result.stdout


def test_run_command_accepts_config_and_task(tmp_path):
    config_path = tmp_path / "safeloop.yml"
    config_path.write_text(
        f"workspace: {tmp_path}\n"
        "test_command: python -c \"print('ok')\"\n"
        "llm_provider: mock\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safeloop",
            "run",
            "--config",
            str(config_path),
            "--task",
            "verify",
            "--mock-response",
            '{"tool_name":"finish","arguments":{"message":"done"},"reason":"done","expected_outcome":"stop"}',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "finished" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v`

Expected: FAIL because `demo` and `run` commands are not wired.

- [ ] **Step 3: Write minimal implementation**

Wire CLI subcommands to state machine and create the deterministic sample project. The demo must not call a real provider.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v`

Expected: PASS.

- [ ] **Step 5: Run demo manually**

Run: `python -m safeloop demo`

Expected: Exit 0 and output contains `guardrail_blocked`, `feedback_added`, and `finished`.

- [ ] **Step 6: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 7: Commit and log**

```bash
git add safeloop/cli.py safeloop/demo.py tests/test_demo.py tests/test_cli_bootstrap.py samples Makefile PLAN.md AGENT_LOG.md
git commit -m "feat(task-12): add cli commands and mechanism demo"
```

Update `PLAN.md` Task 12 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 13: FastAPI WebUI and JSON API

**Goal:** 提供最小可用 WebUI/API，展示任务提交、run 状态、事件日志、健康检查和机制演示入口。

**Files:**
- Create: `safeloop/web.py`
- Create: `tests/test_web.py`
- Modify: `safeloop/cli.py`
- Modify: `pyproject.toml`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: `RunManager`, `EventLogStore`, `AgentStateMachine`
- Produces: `create_app() -> FastAPI`
- Produces: `GET /health`
- Produces: `GET /`
- Produces: `POST /api/runs`
- Produces: `GET /api/runs/{run_id}`
- Produces: `GET /api/runs/{run_id}/events`
- Produces: `POST /api/demo`
- Produces: `python -m safeloop web --host 0.0.0.0 --port 8000`

**Expected Implementation:**
- API 默认使用 mock LLM。
- `/` 返回简单 HTML，不引入前端构建系统。
- `POST /api/runs` 接收 `task`, `config_path`, 可选 `mock_responses`。
- 缺失 run 返回 404。
- WebUI 不显示 secret，事件 payload 使用 redaction。

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_web.py
from pathlib import Path

from fastapi.testclient import TestClient

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_web.py -v`

Expected: FAIL with missing `safeloop.web`.

- [ ] **Step 3: Write minimal implementation**

Implement FastAPI app, JSON endpoints, simple HTML, and CLI web command.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_web.py -v`

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 6: Commit and log**

```bash
git add safeloop/web.py safeloop/cli.py tests/test_web.py pyproject.toml PLAN.md AGENT_LOG.md
git commit -m "feat(task-13): add fastapi webui"
```

Update `PLAN.md` Task 13 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 14: Credential Manager and DeepSeek Client

**Goal:** 实现真实 LLM 凭据安全管理和 DeepSeek client，同时保证测试不依赖网络或真实 key。

**Files:**
- Create: `safeloop/credentials.py`
- Create: `safeloop/llm/deepseek.py`
- Create: `tests/test_credentials.py`
- Create: `tests/test_deepseek_client.py`
- Modify: `safeloop/cli.py`
- Modify: `safeloop/llm/__init__.py`
- Modify: `tests/test_cli_bootstrap.py` if needed for implemented `credentials` behavior
- Modify: `PLAN.md`
- Modify: `AGENT_LOG.md`
- Create: `.superpowers/sdd/task-14-report.md`

**Interfaces:**
- Consumes: `HarnessConfig`, `LLMRequest`
- Produces: `class CredentialManager`
- Produces: `CredentialManager.status(provider: str) -> dict[str, str]`
- Produces: `CredentialManager.set_key(provider: str, key: str) -> None`
- Produces: `CredentialManager.get_key(provider: str) -> str | None`
- Produces: `CredentialManager.clear_key(provider: str) -> None`
- Produces: `class DeepSeekClient`
- Produces: `DeepSeekClient.complete(request: LLMRequest) -> str`
- Produces CLI: `python -m safeloop credentials status|set|clear --provider deepseek`

**Expected Implementation:**
- `keyring` 是默认 backend，service name 为 `safeloop-agent`。
- `env` backend 读取 `DEEPSEEK_API_KEY`。
- `dotenv` backend 读取 workspace 或当前目录 `.env`，但不写入 git。
- `credentials status` 只输出 `configured` 或 `missing`，不输出 key。
- `credentials set` 使用 `getpass.getpass()` 隐藏输入。
- DeepSeek client 使用 OpenAI-compatible chat completions HTTP API；单元测试使用 `httpx.MockTransport`。

- [x] **Step 1: Write the failing tests**

```python
# tests/test_credentials.py
from safeloop.credentials import CredentialManager


def test_keyring_backend_status_without_revealing_key(monkeypatch):
    saved = {}

    monkeypatch.setattr("keyring.set_password", lambda service, user, key: saved.update({(service, user): key}))
    monkeypatch.setattr("keyring.get_password", lambda service, user: saved.get((service, user)))
    monkeypatch.setattr("keyring.delete_password", lambda service, user: saved.pop((service, user), None))

    manager = CredentialManager(backend="keyring")
    manager.set_key("deepseek", "sk-secret")

    status = manager.status("deepseek")

    assert status == {"provider": "deepseek", "status": "configured"}
    assert "sk-secret" not in str(status)


def test_env_backend_reads_deepseek_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")

    manager = CredentialManager(backend="env")

    assert manager.get_key("deepseek") == "sk-env"
```

```python
# tests/test_deepseek_client.py
import httpx

from safeloop.llm.base import LLMRequest
from safeloop.llm.deepseek import DeepSeekClient


def test_deepseek_client_uses_http_transport_without_real_network():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"tool_name":"finish","arguments":{"message":"done"},"reason":"done","expected_outcome":"stop"}'
                        }
                    }
                ]
            },
        )

    client = DeepSeekClient(
        api_key="sk-test",
        model="deepseek-chat",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    raw = client.complete(LLMRequest(task="finish", feedback=[], memories=[], events=[]))

    assert '"finish"' in raw
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v`

Observed RED: collection failed with `ModuleNotFoundError: No module named 'safeloop.credentials'` and `ModuleNotFoundError: No module named 'safeloop.llm.deepseek'`.

- [x] **Step 3: Write minimal implementation**

Implement credential backends and DeepSeek client. Do not store or print any real key in tests, logs, README, or config samples.

- [x] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v`

Observed GREEN: `12 passed in 0.56s`.

- [x] **Step 5: Run secret scan commands**

Run: `Get-ChildItem -Recurse -File | Select-String -Pattern 'sk-'`

Observed: matches are limited to dummy placeholders in tests, docs, and generated `.pyc` cache entries such as `sk-test`, `sk-secret`, `sk-env`, and existing redaction/test fixtures; no real API key appeared.

- [x] **Step 6: Run full tests**

Run: `python -m pytest -v`

Observed GREEN: `65 passed in 1.70s`.

- [x] **Step 7: Commit and log**

```bash
git add safeloop/credentials.py safeloop/llm/deepseek.py safeloop/cli.py tests/test_credentials.py tests/test_deepseek_client.py PLAN.md AGENT_LOG.md
git commit -m "feat(task-14): add credential manager and deepseek client"
```

Implementation commit: `68b0c96` (`feat(task-14): add credential manager and deepseek client`).

Hash traceability note: the real implementation hash was recorded in a follow-up process commit because a commit cannot embed its own final hash without changing that hash.

Review-fix commit: `4e0af51` (`fix(task-14): harden credentials and deepseek errors`).

---

### Task 15: CI, Docker Distribution, and README

**Goal:** 满足一键测试、GitHub Actions、`.gitlab-ci.yml`、Docker 分发和 README 运行说明要求。

**Files:**
- Create: `Dockerfile`
- Create: `.github/workflows/ci.yml`
- Create: `.gitlab-ci.yml`
- Create: `README.md`
- Create: `tests/test_distribution_files.py`
- Modify: `Makefile`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: CLI commands, demo command, WebUI command, tests
- Produces: `make test`
- Produces: `make demo`
- Produces: `make web`
- Produces: `docker build -t safeloop-agent .`
- Produces: `docker run -p 8000:8000 safeloop-agent`
- Produces GitHub Actions jobs: `test`, `demo`, `docker-build`
- Produces GitLab CI job: `unit-test`

**Expected Implementation:**
- GitHub Actions on push and pull request runs Python setup, `python -m pytest`, `python -m safeloop demo`, and Docker build.
- `.gitlab-ci.yml` includes `unit-test` job running `python -m pytest`.
- Docker image starts WebUI on `0.0.0.0:8000` in mock mode by default.
- README contains exact sections: Project Overview, Installation, Running, Distribution, Credential Security, Safety Boundaries, Directory Structure, Testing, CI/CD, Known Limits.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_distribution_files.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_distribution_files.py -v`

Expected: FAIL because distribution files do not exist.

- [ ] **Step 3: Write minimal implementation**

Create Docker, CI, Makefile and README content. CI must use mock LLM only.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_distribution_files.py -v`

Expected: PASS.

- [ ] **Step 5: Run local acceptance commands**

Run: `make test`

Expected: PASS.

Run: `python -m safeloop demo`

Expected: Exit 0 and output contains `guardrail_blocked`, `feedback_added`, and `finished`.

Run: `docker build -t safeloop-agent .`

Expected: Docker image builds successfully.

- [ ] **Step 6: Commit and log**

```bash
git add Dockerfile .github/workflows/ci.yml .gitlab-ci.yml README.md Makefile tests/test_distribution_files.py PLAN.md AGENT_LOG.md
git commit -m "chore(task-15): add ci docker and readme"
```

Update `PLAN.md` Task 15 with the commit hash and append an `AGENT_LOG.md` entry.

---

### Task 16: Process Documents and Final Acceptance Evidence

**Goal:** 完成课程过程证据，确保 `SPEC_PROCESS.md`、`AGENT_LOG.md`、`REFLECTION.md` 框架和最终验收命令可追踪。

**Files:**
- Create: `REFLECTION.md`
- Modify: `SPEC_PROCESS.md`
- Modify: `AGENT_LOG.md`
- Modify: `PLAN.md`
- Modify: `README.md`
- Create: `tests/test_process_docs.py`

**Interfaces:**
- Consumes: commit history, PR links, CI run URL, cold-start notes
- Produces: `SPEC_PROCESS.md` with brainstorming and cold-start validation record
- Produces: `AGENT_LOG.md` chronological implementation evidence
- Produces: `REFLECTION.md` outline for human-written final reflection

**Expected Implementation:**
- `SPEC_PROCESS.md` includes at least 3 key brainstorming iterations and cold-start validation findings.
- `AGENT_LOG.md` entries include timestamp, task number, Superpowers skill, key prompt/context, subagent output or commit hash, human intervention and lesson learned.
- `REFLECTION.md` includes headings only or student-authored content. Do not use AI to write the final 1500-2500 word reflection body unless the course explicitly allows AI polishing with disclosure.
- README links to CI run, Docker command and deployed WebUI URL when available.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_process_docs.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_process_docs.py -v`

Expected: FAIL until process documents contain required sections.

- [ ] **Step 3: Write minimal documentation structure**

Create or update the process documents using real process evidence from this project. `REFLECTION.md` may contain headings and notes for the student to complete personally.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_process_docs.py -v`

Expected: PASS.

- [ ] **Step 5: Run final local verification**

Run: `make test`

Expected: PASS.

Run: `python -m safeloop demo`

Expected: Exit 0 and output contains `guardrail_blocked`, `feedback_added`, and `finished`.

Run: `docker build -t safeloop-agent .`

Expected: Docker image builds successfully.

- [ ] **Step 6: Commit and log**

```bash
git add SPEC_PROCESS.md AGENT_LOG.md REFLECTION.md README.md tests/test_process_docs.py PLAN.md
git commit -m "docs(task-16): add process evidence documents"
```

Update `PLAN.md` Task 16 with the commit hash and append the final `AGENT_LOG.md` entry.

---

## Review Gates for Every Task

Each task must pass two review gates before moving to the next task:

1. **Spec compliance review**
   - Verify the task implements only the relevant `SPEC.md` requirements.
   - Verify no implementation relies on prompt-only safety.
   - Verify mock LLM tests remain deterministic and offline.

2. **Code quality review**
   - Verify module boundaries remain focused.
   - Verify public interfaces match this `PLAN.md`.
   - Verify errors are structured and testable.
   - Verify logs and events are redacted.
   - Verify tests fail before implementation and pass after implementation.

Critical issues must be fixed before the next task starts.

---

## Final Acceptance Checklist

- [ ] `SPEC.md` contains all required sections and A-project mechanism design.
- [ ] `PLAN.md` contains task dependencies, parallel work and TDD validation steps.
- [ ] `SPEC_PROCESS.md` records brainstorming, at least 3 iterations, AI suggestions accepted/rejected, and cold-start validation.
- [ ] `AGENT_LOG.md` records each task with timestamp, skill, prompt/context, subagent output or commit hash, human intervention and lesson.
- [ ] `make test` passes locally.
- [ ] `python -m safeloop demo` deterministically shows guardrail block, feedback loop and successful finish.
- [ ] GitHub Actions passes on the final push.
- [ ] `.gitlab-ci.yml` includes a passing `unit-test` job.
- [ ] Docker image builds.
- [ ] README explains installation, running, Docker distribution, key security, safety boundaries, CI/CD and known limits.
- [ ] No real credentials are present in repository files or git history.
- [ ] Final PR descriptions mention subagent ownership and human modifications.
- [ ] `REFLECTION.md` is written by the student and stays within the course word range.
