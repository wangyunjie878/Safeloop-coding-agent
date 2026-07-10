# SPEC.md：SafeLoop Coding Agent Harness

## 1. 问题陈述

SafeLoop 要解决的问题是：如何把一个只会生成“下一步想法”的 LLM，封装成一个能在软件开发场景中稳定工作的 Coding Agent Harness。Codex、Claude Code 这类工具的可靠性并不只来自模型本身，还来自外层 harness：它负责组织上下文、解析模型动作、分发工具、运行测试、把结果反馈给下一轮、拦截危险操作，并决定任务何时继续或停止。

本项目实现一个轻量级、教学型的 Coding Agent Harness。SafeLoop 能在用户指定的本地代码工作区内读取和修改代码，执行配置好的命令，运行测试，观察失败，并把这些客观结果反馈给下一轮 LLM，从而形成多轮自我修正。

目标用户是维护本地代码库的软件开发者，尤其是希望使用 coding agent 辅助完成小型 bug 修复、测试修复和局部功能变更的开发者。这类用户需要 agent 操作真实项目文件，但同时要求 agent 的行为有边界、可观察、可审计、可复现。

SafeLoop 值得做，因为它展示了可靠 coding agent 背后的工程层。它不是普通聊天机器人，也不是单次 LLM 代码生成包装器。它的核心贡献是一个可测试的 harness 内核，用来协调结构化 LLM 动作、工具分发、治理护栏、测试反馈、记忆和配置。

## 2. 用户故事

以下用户故事面向 SafeLoop 的真实用户：软件开发者。每条故事都尽量满足 INVEST 原则，即独立、可协商、有价值、可估算、小粒度、可测试。

1. 作为代码库维护者，我希望提交一个自然语言代码任务并选择本地 workspace，以便 agent 能从我的真实项目上下文开始工作。
2. 作为软件开发者，我希望 agent 只能列出和读取 workspace 中允许访问的文件，以便它在修改代码前先理解真实代码。
3. 作为软件开发者，我希望 agent 能在允许路径内修改代码文件，以便完成小型 bug 修复、测试修复或局部功能变更。
4. 作为依赖自动化检查的开发者，我希望 agent 能运行我配置的 test、lint 或 build 命令，以便用客观项目反馈判断修改是否正确。
5. 作为 coding agent 用户，我希望 agent 能把测试失败信息纳入下一轮决策，以便它不是一次性生成代码，而是能根据失败结果继续修正。
6. 作为担心本地误操作的开发者，我希望危险命令、敏感文件和 workspace 外路径被拦截或要求确认，以便保护我的代码库、凭据和本地环境。
7. 作为需要信任 agent 行为的开发者，我希望 WebUI 展示每轮动作、工具结果、测试输出、反馈摘要和护栏决策，以便理解和审计整个运行过程。
8. 作为需要在 CI 中验证工具可靠性的开发者，我希望核心 harness 机制能使用 mock LLM 离线测试，以便不配置真实 API key 也能验证工具分发、护栏、反馈和停机逻辑。

## 3. 功能规约

### 3.1 任务入口模块

- 输入：用户任务、workspace 路径、配置文件路径、LLM 模式。
- 行为：校验 workspace，加载配置，创建一次 run，初始化状态和事件日志。
- 输出：`run_id`、初始 run 状态、配置摘要；`--help` 输出项目名称 `SafeLoop Coding Agent Harness` 和子命令列表；`--version` 输出格式为 `safeloop <version>`。
- 边界条件：任务为空、workspace 不存在、workspace 不可读、配置文件缺失、配置字段非法。
- 错误处理：返回配置错误或输入错误，不进入 agent 主循环。

### 3.2 LLM 抽象模块

- 输入：系统上下文、用户任务、可用工具 schema、历史工具结果、反馈摘要、相关记忆。
- 行为：通过统一的 `LLMClient` 接口调用模型。实现包括用于测试的确定性 `MockLLMClient` 和用于真实运行的 DeepSeek V4 client。
- 输出：标准化 `AgentAction`，包含工具名、参数、原因和预期结果。
- 边界条件：LLM 输出不是合法 JSON、工具名不存在、参数缺失、provider 调用失败、rate limit、API key 缺失。
- 错误处理：记录 `parse_error` 或 `provider_error`；只有配置为可恢复的错误才重试，否则安全停止。

### 3.3 执行状态机模块

- 输入：当前 run 状态、解析后的 `AgentAction`、配置、事件历史、记忆上下文。
- 行为：按 `INIT -> CONTEXT -> DECIDE -> GUARD -> DISPATCH -> OBSERVE -> FEEDBACK -> FINISH/STOP` 流转。
- 输出：更新后的 run 状态、事件日志、继续或停止决策。
- 边界条件：达到最大步数、重复失败次数过多、收到 `finish` 动作、不可恢复工具错误、护栏拒绝。
- 错误处理：进入 `STOP` 状态，记录停止原因，并保留最后一次安全上下文摘要。

### 3.4 工具分发模块

- 输入：工具名、工具参数、run context。
- 行为：在工具注册表中查找工具，校验参数 schema，调用工具实现，并标准化结果。
- 输出：`ToolResult`，包含成功标记、摘要、stdout、stderr、exit code、耗时等字段。
- 边界条件：未知工具、参数格式错误、工具超时、工具内部异常。
- 错误处理：返回结构化 `tool_error`，而不是让异常直接中断进程。

### 3.5 文件工具模块

- 输入：相对文件路径、可选读取范围、patch 内容或写入内容。
- 行为：列出文件、读取文件、应用 patch、或写入允许路径内的文件。
- 输出：文件列表、文件内容、patch 摘要或写入摘要。
- 边界条件：路径逃出 workspace、路径在 blocklist 中、文件不存在、二进制文件、文件过大、编码不支持。
- 错误处理：拒绝操作，返回 `file_error`，并保证不会修改文件。

### 3.6 命令与测试工具模块

- 输入：shell 命令、工作目录、超时时间，或配置中的 `test_command`、`lint_command`、`build_command`。
- 行为：在 workspace 内执行允许的命令，收集 exit code、stdout、stderr 和耗时。
- 输出：命令执行结果；测试命令额外输出通过或失败状态。
- 边界条件：命令被 blocklist 拦截、命令不在 allowlist 中、命令包含危险模式、执行超时、输出过长、可执行文件不存在。
- 错误处理：拒绝不安全命令；截断过长输出；将 timeout、command failure 或 test failure 交给反馈分类模块。

### 3.7 治理护栏模块

- 输入：`AgentAction`、路径、命令字符串、配置中的 allowlist、blocklist 和 approval rules。
- 行为：检查 workspace 边界、敏感文件名、破坏性命令、发布命令、部署命令和凭据访问风险。
- 输出：`GuardrailDecision`，取值为 `allow`、`deny` 或 `require_approval`，并包含风险等级、原因和命中的规则。
- 边界条件：规则冲突、动作字段缺失、未知风险等级、命令含义模糊。
- 错误处理：默认拒绝，并记录 `guardrail_blocked` 事件。

### 3.8 反馈分类模块

- 输入：`ToolResult`、命令输出、测试输出、解析错误、护栏决策。
- 行为：将结果分类为 `test_failure`、`syntax_error`、`timeout`、`guardrail_blocked`、`tool_error`、`parse_error` 或 `generic_failure`。
- 输出：压缩后的 `Feedback`，进入下一轮 LLM 上下文。
- 边界条件：输出过长、测试框架未知、多个错误类型混杂、日志格式不结构化。
- 错误处理：使用 `generic_failure`，保留短原始片段，并标记是否发生截断。

### 3.9 记忆模块

- 输入：记忆内容、标签、scope、来源 run id、查询上下文。
- 行为：保存和检索项目规则、历史决策、常见失败、用户偏好。
- 输出：筛选后的 `MemoryEntry` 列表。
- 边界条件：记忆文件不存在、条目过多、没有标签匹配、记忆数据格式损坏。
- 错误处理：缺失时初始化空记忆；读取失败时返回空列表并记录 warning。

### 3.10 WebUI 与 API 模块

- 输入：任务提交请求、run 查询、事件查询、health check、demo 请求。
- 行为：通过最小 FastAPI WebUI 和 JSON API 提供任务提交、状态查看、事件日志、机制演示和健康检查。
- 输出：HTML 页面或 JSON 响应。
- 边界条件：`run_id` 不存在、并发 run 冲突、服务重启、后台任务失败。
- 错误处理：缺失 run 返回 404；状态冲突返回 409；未知服务器错误返回 500 并记录 API 错误。

### 3.11 凭据管理模块

- 输入：provider 名称、key 来源、凭据状态 / 更新 / 清除命令。
- 行为：从批准的来源读取 DeepSeek API key，报告 key 是否已配置，支持更新或清除本地凭据状态，并且永不回显明文 key。
- 输出：`credential_status` 和 provider 可用性。
- 边界条件：key 缺失、key 格式异常、CI mock 模式、真实 LLM 模式未配置凭据。
- 错误处理：真实 provider 模式缺少 key 时拒绝启动；mock 模式不需要任何 key。

## 4. 非功能性需求

### 4.1 性能

- 默认单次 run 最多执行 10 个 LLM-action 步骤，并允许配置。
- 默认单个命令超时时间为 60 秒，并允许配置。
- 工具输出进入下一轮 LLM 上下文前必须截断和摘要化。
- 文件读取默认拒绝或摘要化过大文件，默认单文件读取上限为 200 KB。
- WebUI 查询状态和日志时，应在 1 秒内返回已有 run 数据，不等待长时间工具执行完成。

### 4.2 安全与凭据威胁模型

SafeLoop 的安全目标是：让 agent 保持在用户选择的 workspace 中行动，防止凭据泄露，并用代码级护栏处理高风险动作。

凭据威胁与对策：

- 威胁：真实 DeepSeek API key 被硬编码进源码。对策：真实 key 不得出现在源码、配置模板、测试数据或文档示例中。
- 威胁：key 被写入日志、WebUI 输出或事件记录。对策：事件输出必须经过 secret redaction；凭据状态只显示 `configured` 或 `missing`。
- 威胁：key 被提交到 GitHub。对策：OS keyring 作为默认安全存储；`.env` 仅作为开发和容器环境的可选来源并加入 `.gitignore`；README 明确禁止提交 secrets；CI 默认使用 mock LLM。
- 威胁：LLM 要求读取 `.env`、SSH key、shell history 或凭据文件。对策：护栏阻止敏感文件名和 workspace 外路径。
- 威胁：LLM 要求执行破坏性或发布类命令。对策：护栏拒绝或要求确认 `rm -rf`、数据库删除、`git push`、`docker push`、部署命令和系统目录修改。

第一版凭据存储方案：

- CI 和测试使用 mock LLM，不需要任何 secret。
- 本地真实 LLM 模式优先从 OS keyring 读取 `DEEPSEEK_API_KEY`。
- `.env` 和环境变量作为开发、容器和 CI 场景的可选来源。
- 文档必须说明 `.env` 是明文文件，进程环境变量也可能被本机进程观察到。
- CLI 必须支持凭据状态、隐藏输入录入、更新和清除流程，但不显示明文 key。
- 如果 OS keyring 在目标平台不可用，CLI 必须给出清晰错误，并提示用户改用 `.env` 或环境变量来源。

### 4.3 可用性

- CLI 命令覆盖任务运行、机制演示、凭据状态、测试运行和 WebUI 启动。
- 配置文件字段清晰，例如 `workspace`、`test_command`、`allowed_paths`、`blocked_paths`、`blocked_commands`、`llm_provider`。
- 错误信息必须说明失败原因和用户可采取的修复方式。
- WebUI 聚焦任务提交、run 状态、事件日志、护栏决策和测试反馈。

### 4.4 可观测性

- 每次 run 记录结构化事件，包括状态变化、LLM 动作、工具调用、护栏决策、命令结果、反馈摘要和停止原因。
- CLI 与 WebUI 都能查看 run 事件。
- 长输出以片段形式保存，并标明是否截断。
- 日志不得包含原始 API key、`.env` 内容、SSH key 或其他敏感内容。
- 测试必须断言关键事件存在，例如 `guardrail_blocked`、`test_failure`、`feedback_added` 和 `finished`。

## 5. 系统架构

### 5.1 组件图

SafeLoop 包含以下组件：

- CLI Entry：本地命令行入口，用于运行任务、机制演示、测试和凭据检查。
- WebUI Entry：FastAPI 应用，用于任务提交和事件查看。
- Run Manager：创建 run、保存 run 状态、协调状态机。
- Agent State Machine：拥有主循环和停机条件。
- Config Loader：读取并校验 harness 配置。
- Memory Store：读取和写入项目记忆。
- LLM Client：抽象 mock LLM 和 DeepSeek V4。
- Action Parser：校验结构化 LLM 动作。
- Guardrail Engine：执行动作前的风险检查。
- Tool Dispatcher：注册工具并调用工具实现。
- Tool Implementations：文件、命令、测试、记忆和 finish 工具。
- Feedback Classifier：把工具输出转成下一轮上下文可用的反馈。
- Event Log Store：记录所有 run 事件，供 CLI、WebUI 和测试使用。

### 5.2 数据流

```text
用户任务
-> Run Manager 创建 run
-> Config Loader 校验 workspace 和规则
-> Memory Store 返回相关记忆
-> State Machine 构造上下文
-> LLM Client 返回结构化 action
-> Action Parser 校验 action
-> Guardrail Engine 判断 allow / deny / require_approval
-> Tool Dispatcher 执行允许的工具
-> ToolResult 写入 Event Log
-> Feedback Classifier 生成反馈
-> State Machine 决定继续、修复、验证、完成或停止
```

### 5.3 外部依赖

- DeepSeek V4 API：用于可选真实 LLM 执行。
- Python runtime：用于运行 harness。
- FastAPI：用于 WebUI 和 API。
- pytest：用于确定性单元测试。
- Docker：用于分发。
- GitHub Actions：用于 CI。
- 用户项目命令：例如 `pytest`、`npm test`、`go test ./...`、`mvn test`、`cargo test`，由用户配置。

## 6. 数据模型

### 6.1 Run

- `id`：唯一 run id。
- `task`：用户任务文本。
- `workspace`：workspace 绝对路径。
- `status`：`created`、`running`、`waiting_approval`、`finished`、`stopped` 或 `failed`。
- `current_step`：当前循环步数。
- `max_steps`：最大允许步数。
- `created_at`：创建时间。
- `finished_at`：可选完成时间。

### 6.2 AgentAction

- `tool_name`：请求调用的工具。
- `arguments`：结构化工具参数。
- `reason`：模型给出的动作原因。
- `expected_outcome`：模型预期的执行结果。

约束：`tool_name` 必须存在于工具注册表中，`arguments` 必须符合工具 schema。

### 6.3 ToolResult

- `tool_name`：已执行工具。
- `success`：是否成功。
- `exit_code`：可选进程退出码。
- `stdout`：标准输出片段。
- `stderr`：标准错误片段。
- `summary`：人类可读摘要。
- `duration_ms`：工具耗时。

约束：进入上下文的 stdout 和 stderr 必须限制长度。

### 6.4 GuardrailDecision

- `decision`：`allow`、`deny` 或 `require_approval`。
- `risk_level`：`low`、`medium`、`high` 或 `critical`。
- `reason`：决策说明。
- `matched_rule`：命中的规则。

约束：模糊的高风险动作默认 `deny`。

### 6.5 Feedback

- `kind`：`test_failure`、`syntax_error`、`timeout`、`guardrail_blocked`、`tool_error`、`parse_error` 或 `generic_failure`。
- `summary`：给下一轮 LLM 的简洁说明。
- `raw_excerpt`：选取的原始输出片段。
- `suggested_next_context`：加入下一轮 prompt 的简要上下文。

约束：原始片段必须脱敏并限制长度。

### 6.6 MemoryEntry

- `id`：唯一记忆 id。
- `scope`：project、run 或 user。
- `tags`：可检索标签。
- `content`：记忆文本。
- `created_at`：创建时间。
- `source_run_id`：可选来源 run id。

约束：记忆中不得保存原始 secret。

### 6.7 HarnessConfig

- `workspace`：目标项目目录。
- `allowed_paths`：agent 可读写路径。
- `blocked_paths`：agent 禁止访问路径。
- `test_command`：测试命令。
- `lint_command`：可选 lint 命令。
- `build_command`：可选 build 命令。
- `blocked_commands`：禁止命令模式。
- `approval_required_commands`：需要确认的命令模式。
- `llm_provider`：`mock` 或 `deepseek`。
- `model`：模型名称；DeepSeek 模式下由用户在配置中指定具体 DeepSeek V4 model id，代码不硬编码真实模型名。
- `credential_backend`：`keyring`、`env` 或 `dotenv`。
- `max_steps`：最大 agent loop 步数。

约束：路径默认相对于 `workspace` 解析，除非策略明确允许绝对路径。

### 6.8 Event

- `run_id`：关联 run id。
- `step`：循环步数。
- `type`：事件类型。
- `payload`：结构化事件数据。
- `created_at`：创建时间。

约束：事件 payload 展示前必须经过脱敏处理。

## 7. 凭据与分发设计

### 7.1 凭据流程

SafeLoop 支持 mock 模式和真实 DeepSeek 模式。

mock 模式：

- 用于测试、CI 和机制演示。
- 不需要 API key。
- GitHub Actions 默认使用该模式。

DeepSeek 模式：

- 使用 `DEEPSEEK_API_KEY`。
- 默认从 OS keyring 读取 key。
- 可配置为从环境变量或本地 `.env` 文件读取 key，用于容器、教学演示或平台不支持 keyring 的场景。
- 提供 CLI 命令用于隐藏输入录入、查看凭据状态、更新和清除。
- 永不打印明文 key。
- key 缺失时拒绝启动真实 provider 模式。

### 7.2 分发形态

主要分发产物是 Docker 镜像。README 必须包含：

```bash
docker build -t safeloop-agent .
docker run -p 8000:8000 safeloop-agent
```

README 还应说明本地 Python 开发运行方式：

```bash
python -m pytest
python -m safeloop demo
python -m safeloop web
```

### 7.3 目标平台

- 主要平台：Linux container。
- 开发平台：Windows 和 Linux with Python。
- CPU 架构：默认 x86_64。

### 7.4 CI/CD

GitHub Actions 每次 push 必须运行：

- 使用 mock LLM 的单元测试。
- 机制演示。
- 可选 lint / type checks。
- Docker image build。

由于作业最终清单提到 `.gitlab-ci.yml` 和 `unit-test` job，仓库可额外提供一个兼容 GitLab CI 的 `unit-test` job，运行同一套 mock 测试命令。

## 8. 技术选型与理由

- Python：适合快速实现 agent loop、工具系统、配置和测试。
- FastAPI：轻量，适合实现 WebUI 和 JSON API。
- pytest：适合确定性单元测试和 mock LLM 场景。
- Docker：满足可复现分发和部署要求。
- GitHub Actions：满足每次 push 自动 CI 的要求。
- DeepSeek V4：作为可选真实 LLM provider，通过 OpenAI-compatible 接口接入。
- mock LLM：作为测试和 CI 默认 provider，确保核心机制不依赖网络或真实 key。
- keyring：作为第一版真实 LLM key 的默认安全存储。
- YAML 或 TOML 配置：适合表达项目级 harness 规则。

如果 WebUI 包含自定义前端样式，将遵循 Open Design 的工具型界面原则：信息密度适中、状态清楚、减少装饰、突出任务执行和审计。

## 9. 验收标准

- 用户能通过 CLI 提交任务并获得 `run_id`。
- 用户能通过 WebUI 提交或查看 run。
- 状态机能完成至少一次 mock LLM 驱动的完整 run。
- Action Parser 能拒绝格式错误或未知工具动作。
- Tool Dispatcher 能路由已注册工具并拒绝未知工具。
- 文件工具能读取和修改允许路径内文件。
- 文件工具能拒绝 workspace 外路径。
- 命令工具能运行配置好的测试命令并收集输出。
- Guardrail 能拦截至少一个危险命令，例如 `rm -rf /`。
- Guardrail 能拦截至少一个敏感文件访问，例如 `.env`。
- 测试失败能被摘要化并进入下一轮 LLM 上下文。
- mock LLM 测试能证明注入失败反馈后，下一轮动作发生变化。
- 记忆模块能保存和读取 project scope 记忆。
- Event log 包含状态变化、工具调用、反馈和护栏决策。
- 日志和 WebUI 不显示 API key。
- GitHub Actions 在没有真实 LLM key 的情况下通过。
- Docker 镜像能成功构建。
- 机制演示能确定性复现：
  1. 护栏拦截危险动作；
  2. 注入失败后下一轮动作改变；
  3. 工具分发与执行状态机完整流转。

## 10. 风险与未决问题

- 真实 LLM 输出可能不稳定，因此结构化 action parsing 和 parse-error recovery 必须严格。
- 支持任意语言容易扩大范围。第一版通过配置 test、lint、build 命令保持语言无关，而不做语言专用 AST 分析。
- Docker 中运行任意用户项目测试可能缺少项目依赖。第一版在 CI 中使用受控示例项目，并在 README 中说明用户项目依赖需要自行提供。
- WebUI 可能分散对 harness 内核的精力。第一版 WebUI 保持最小可用，以审计和观察为核心。
- OS keyring 在不同平台表现可能不同。第一版必须覆盖 keyring 不可用时的错误提示，并允许用户在容器中改用 `.env` 或环境变量。
- 陌生 agent 冷启动验证可能暴露 SPEC 或 PLAN 中的隐含假设。这些问题必须记录进 `SPEC_PROCESS.md`，并在实现前修订。
- 执行 shell 命令天然有风险。SafeLoop 必须对模糊高风险动作默认拒绝。

## 11. 领域与机制设计

### 11.1 Coding 领域的反馈信号

SafeLoop 的客观反馈信号包括：

- 配置的测试命令 exit code 和输出；
- 配置的 lint 命令 exit code 和输出；
- 配置的 build 命令 exit code 和输出；
- 护栏 allow / deny / require_approval 决策；
- parser 和 schema 校验结果；
- 工具执行成功或失败结果。

这些信号是确定性的，可以回灌进 agent loop，而不是让 LLM 自行判断“自己是否做对”。

### 11.2 危险动作

危险动作包括：

- 删除大量目录或 root-like 路径；
- 访问 workspace 外路径；
- 读取 `.env`、SSH key、token 文件或 shell history；
- 执行发布或部署命令；
- push 到远程仓库；
- 删除数据库或执行破坏性数据库命令；
- 修改系统目录或用户 home 配置文件。

这些动作必须由代码级 guardrail 处理，不能只依赖 prompt 提醒。

### 11.3 所需工具

第一版包含：

- `list_files`
- `read_file`
- `patch_file` 或 `write_file`
- `run_command`
- `run_tests`
- `save_memory`
- `load_memory`
- `finish`

所有工具都注册在 dispatcher 中，经过 schema 校验，并返回统一结果。

### 11.4 记忆需求

SafeLoop 保存：

- 项目规则和约定；
- 用户偏好；
- 历史失败与摘要；
- run 中做出的决策；
- 常用测试命令和验证说明。

记忆检索必须由代码实现，并能使用 mock data 测试。

### 11.5 主要贡献

SafeLoop 的主要贡献是 **工具分发与执行状态机设计**。

LLM 可以提出动作，但 harness 拥有主循环：

```text
context -> LLM action -> parse -> guard -> dispatch -> observe -> feedback -> stop/continue
```

该机制可以在没有真实 LLM 的情况下，通过脚本化的 `MockLLMClient` 测试。mock 测试必须验证：

- 合法 action 能到达正确工具；
- 非法 action 会被拒绝；
- 危险 action 在执行前被拦截；
- 测试失败会产生 feedback；
- 下一轮 LLM 上下文能收到 feedback；
- run 只会因为显式 finish、最大步数限制或不可恢复错误而停止。

这满足作业要求：移除不确定的真实 LLM 后，核心 harness 机制仍然能被确定性单元测试验证。
