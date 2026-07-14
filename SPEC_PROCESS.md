# SPEC_PROCESS.md：SafeLoop Coding Agent Harness 规约过程记录

本文档记录我与 Superpowers / Codex 协作生成 `SPEC.md` 与 `PLAN.md` 的过程。它对应 `general_requirement.md` 第 4.4 节，并为第 4.5 节冷启动验证预留记录位置。

## 1. 基本信息

- 项目名称：SafeLoop Coding Agent Harness
- 项目类型：A · Coding Agent Harness
- 主开发智能体：OpenAI Codex App with Superpowers
- 主要使用技能：`brainstorming`、`writing-plans`、`verification-before-completion`
- 规约文档：[SPEC.md](./SPEC.md)
- 实现计划：[PLAN.md](./PLAN.md)
- 当前流程阶段：`SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md` 已生成；第 4.5 节冷启动验证已执行，并已将反馈修订回 `SPEC.md` 与 `PLAN.md`。

## Task 16 验收索引

- brainstorming 关键节点：见第 2 节，记录从项目类型、技术栈、语言边界到主贡献选择的关键决策点。
- 关键迭代：见第 3 节，记录至少三轮由用户质询、AI 建议和人工决策共同形成的迭代。
- 冷启动验证：见第 6 节，记录另一个 agent 仅凭 `SPEC.md` 和 `PLAN.md` 执行 Task 1 时暴露的问题。
- SPEC / PLAN 修订：见第 4.3、6.6、6.8 节，记录冷启动反馈如何回写到规约和计划。

## 2. Brainstorming 关键节点

### 2.1 从“做一个 coding agent”收敛到 A 项 Coding Agent Harness

起初我的表述比较宽泛，只说“我要做一个 coding agent”。智能体先根据作业文件解释 A/B/C 的差别，并指出 A 项不是普通聊天机器人，也不是只调一次 LLM 生成代码，而是要实现一个 harness：把 LLM、工具、反馈、护栏、状态机和记忆组织成可运行系统。

这个问题让我修正了原设想：我不再把项目理解成“做个代码智能体界面”，而是理解成“实现一个简易 Codex / Claude Code 背后的 harness 内核”。

### 2.2 明确技术栈、CI 和分发方式

我问过 GitHub Actions、离线测试、Docker、mock LLM 和 DeepSeek 是否会互相影响。智能体建议采用 Python + FastAPI + pytest，Docker 作为分发方式，GitHub Actions 运行 mock LLM 离线测试。

我采纳了这个建议，因为它同时满足作业的测试、分发和凭据治理要求：CI 不需要真实 LLM key；Docker 可以说明别人如何运行；FastAPI 能提供最终要求的 WebUI 接口。

### 2.3 从“支持某种语言”修正为语言无关的 coding harness

我提出“应该要支持任意语言吧”。智能体把范围拆开：SafeLoop 本身用 Python 写，但它操作的目标项目可以是 Python、JavaScript、Go、Java、Rust 等不同语言。语言无关性的实现方式不是为每种语言写 AST 逻辑，而是通过用户配置 `test_command`、`lint_command`、`build_command`。

我采纳了这个方案，因为它既让项目像真实 coding agent，又避免范围膨胀到多语言编译器分析。

### 2.4 明确主要贡献：工具分发与执行状态机

我问“不能其他几个为重要贡献点吗”，因为 harness 的治理、反馈、记忆、工具都很重要。智能体解释：六个维度都要有最低实现，但主贡献最好聚焦一个机制密集、可测试、最能体现 A 项要求的维度。

最后我接受“工具分发与执行状态机”为主要贡献，护栏与测试反馈闭环作为支撑贡献。这个选择让 `SPEC.md` 第 11 节能够回答 A.4 的核心问题：移除真实 LLM 后，工具分发、护栏、反馈和停机仍然可以用 mock LLM 单测验证。

### 2.5 按作业 4.2 修正 SPEC 结构

我多次指出 `SPEC.md` 必须严格匹配 `general_requirement.md` 第 4.2 节，例如：

- 用户故事必须是实际用户的故事，不是开发者实现项目的故事。
- 功能规约必须按模块拆分，并且每项都有输入、行为、输出、边界条件、错误处理。
- 目标用户应该是代码开发者 / 代码库维护者。
- A 项还要额外包含“领域与机制设计”。

这些质询让智能体把文档结构调整成 11 节：第 1 至第 10 节对应通用要求，第 11 节对应 A 项额外要求。

### 2.6 修正凭据安全方案

生成 `PLAN.md` 前，智能体重新检查通用要求第 3.1 节，发现原 `SPEC.md` 把 OS keyring 写成后续扩展，只把 `.env` 作为第一版来源，这不符合“至少实现一种安全存储”的硬性要求。

我接受了这个修正。现在 `SPEC.md` 中的方案是：OS keyring 作为真实 LLM key 的默认安全存储，`.env` 和环境变量只作为开发、容器和 keyring 不可用场景的可选来源。

### 2.7 实现前再次收缩为课程 MVP

进入实现工作流后，我追问“为什么还要 10 多个小时，助教说只要 5 个小时左右”，并进一步明确：不要做得和 Codex 一样，只要一个小代码 agent，能读写代码、执行命令、运行测试，并根据测试结果自我修正。

智能体据此承认前面的时间估计把范围按完整产品级 coding agent 放大了，并把目标修正为课程可验收 MVP：核心机制能跑、mock LLM 测试充分、CI 和过程证据完整，但不实现大型代码索引、复杂交互式终端、无限自动修复、完整 IDE 集成或云端多租户服务。这个修正已经同步到 `SPEC.md` 的 MVP 范围说明和 `PLAN.md` 的 4 个模块 PR 执行轨道。

## 3. 至少三轮关键迭代记录

### 3.1 迭代一：项目类型与目标

对话节选：

```text
我：ABC这三个是啥意思，做一个coding agent不就是做个代码智能体吗
智能体：A 是 Coding Agent Harness，重点不是做普通应用，而是自己实现 agent 主循环、工具、反馈、护栏和记忆。
我：不应该这些都做吗
智能体：基础维度都要做，但需要选择一个主贡献做深。
```

我的处理决策：

- 选择 A · Coding Agent Harness。
- 把目标从“泛泛做代码智能体”改成“做一个简易 Codex / Claude Code 式的本地 coding agent harness”。
- 项目命名保留为 SafeLoop Coding Agent Harness。

### 3.2 迭代二：技术栈与运行方式

对话节选：

```text
我：作业之后要在github上用actions运行什么的，跟这个有影响吗
智能体：CI 应该使用 mock LLM 离线测试，不依赖真实 key。
我：就按你建议的来Python + FastAPI + pytest，Docker 和 GitHub Actions 配置
智能体：可以，核心用 Python，WebUI 用 FastAPI，测试用 pytest，Docker 和 Actions 做分发与自动验证。
```

我的处理决策：

- 采纳 Python + FastAPI + pytest。
- 采纳 Docker 作为主要分发方式。
- 采纳 GitHub Actions 作为 CI，同时在最终计划中加入 `.gitlab-ci.yml` 的 `unit-test` job，以满足最终交付清单。
- 采纳 mock LLM 作为 CI 默认 provider。

### 3.3 迭代三：用户故事和功能规约

对话节选：

```text
我：根据这里面第四大点里4.2，要有至少5个用户故事，遵循INVEST原则，而且这是用户的故事，不是开发者的故事啊
智能体：用户故事应该面向实际使用 SafeLoop 的代码开发者、代码库维护者。
我：功能规约要按模块拆分，每项描述输入 / 行为 / 输出 / 边界条件 / 错误处理。
智能体：将功能规约按任务入口、LLM抽象、状态机、工具分发、文件工具、命令测试工具、护栏、反馈、记忆、WebUI、凭据管理拆分。
```

我的处理决策：

- 要求用户故事改成真实用户视角。
- 要求功能规约逐模块写五要素。
- 最终 `SPEC.md` 包含 8 条用户故事和 11 个功能模块。

### 3.4 迭代四：主贡献与范围控制

对话节选：

```text
我：应该要支持任意语言吧
智能体：SafeLoop 本体用 Python 写，但通过配置测试、lint、build 命令支持多语言项目。
我：感觉老师要我们做一个简易codex或Claude code
智能体：对，它应该读写代码、执行命令、运行测试，并根据结果自我修正。
我：不能其他几个为重要贡献点吗
智能体：六个机制都要有最低实现，但主贡献建议聚焦工具分发与执行状态机。
```

我的处理决策：

- 接受“语言无关但不做多语言 AST 分析”的边界。
- 接受 SafeLoop 是教学型、轻量级本地 Codex / Claude Code，而不是完整商业级 IDE agent。
- 接受“工具分发与执行状态机”为主贡献。

### 3.5 迭代五：SPEC 语言与交付格式

对话节选：

```text
我：这个用中文写可不可以
智能体：可以，中文更适合与作业要求逐项对应。
我：改成中文版
智能体：将 SPEC.md 改成中文版，并自查 4.2 的 10 项和 A 项额外章节。
```

我的处理决策：

- `SPEC.md`、`PLAN.md` 和本过程文档均使用中文。
- 保留必要英文技术名词，例如 FastAPI、pytest、MockLLMClient、DeepSeek、keyring。

### 3.6 迭代六：从“类 Codex 产品”收缩为课程 MVP

对话节选：

```text
我：为什么还要这么久，助教说只要5个小时左右
智能体：我刚才按完整产品级 coding agent 估了；课程 MVP 应该是 5-7 小时。
我：我们做的就是简化版的，不要完整版的！！！
智能体：范围锁定为小型 SafeLoop：读写代码、执行命令、运行测试、根据测试结果做一次受控修正。
我：记住不用做的和codex一样，就是一个小代码agent，它能读写代码、执行命令、运行测试，并根据测试结果自我修正。
```

我的处理决策：

- 明确拒绝完整 Codex / Claude Code 复刻。
- 保留读文件、写文件、执行命令、运行测试、反馈驱动修正和显式 finish 这条最小闭环。
- 把 `PLAN.md` 从 6 个 PR 的偏完整版节奏收缩为 4 个模块 PR。
- 要求后续实现仍保留 TDD、subagent、review、PLAN 更新和 GitHub PR 证据，但功能不要膨胀。

## 4. AI 建议与我的采纳 / 修正

### 4.1 AI 提出且我采纳的建议

- 采纳 A · Coding Agent Harness 作为项目方向。
- 采纳 SafeLoop 作为项目名。
- 采纳 Python + FastAPI + pytest 技术栈。
- 采纳 Docker + GitHub Actions 的分发和 CI 方案。
- 采纳 mock LLM 离线测试核心机制。
- 采纳 DeepSeek V4 作为可选真实 LLM provider。
- 采纳语言无关的命令配置方式，而不是为每种语言实现专门分析器。
- 采纳工具分发与执行状态机作为主要贡献。
- 采纳先 SPEC、再 PLAN、再冷启动验证、再实现的顺序。
- 采纳 OS keyring 作为真实 key 的默认安全存储方案。

### 4.2 AI 提出但我推翻或修正的地方

- 我修正了用户故事的对象：不能写成“开发这个项目的人”的故事，必须写成 SafeLoop 的真实用户，即软件开发者和代码库维护者。
- 我修正了功能规约结构：必须逐模块列出输入、行为、输出、边界条件、错误处理。
- 我要求 `SPEC.md` 严格匹配 4.2 的列表，而不是自由发挥的设计文档。
- 我澄清项目名不需要放弃 SafeLoop，而是保留 SafeLoop。
- 我要求目标用户从偏课程/学生视角改成代码开发者视角。
- 我要求文档改成中文，以便直接对应课程要求。
- 我修正了实现范围：智能体一度按完整类 Codex 产品估算工作量，我明确要求只做课程 MVP 小代码 agent。

### 4.3 AI 建议带来的 SPEC / PLAN 修订

- `SPEC.md` 增加“领域与机制设计”，明确 coding 领域反馈信号、危险动作、工具和记忆需求。
- `SPEC.md` 将 DeepSeek 具体 model id 改为配置项，避免硬编码不稳定的真实模型名。
- `SPEC.md` 将凭据安全方案修正为 OS keyring 默认存储。
- `SPEC.md` 增加 MVP 范围与非目标，明确不复刻完整 Codex / Claude Code。
- `PLAN.md` 增加冷启动验证 gate，强调正式实现前不能写代码。
- `PLAN.md` 将实现拆成 16 个 task，每个 task 都包含失败测试、验证命令和 commit/log 要求。
- `PLAN.md` 增加 MVP 执行模式，并把 GitHub 工作流收缩为 4 个模块 PR。

## 5. Writing-Plans 过程记录

触发 `writing-plans` 前，我明确批准了 `SPEC.md`：

```text
我：SPEC 没问题，开始写 PLAN.md
```

智能体随后读取 `SPEC.md`、`general_requirement.md` 和 A 项项目文件，并按 `writing-plans` 技能要求生成了 `PLAN.md`。计划中的关键设计包括：

- 先写 Pre-Implementation Gate，要求完成冷启动验证。
- 设计根目录、Python 包、测试、samples、CI 和文档文件结构。
- 建立 16 个 task，从 repository bootstrap 到最终过程文档和验收证据。
- 每个 task 都包括失败测试、预期失败、最小实现、验证通过、提交和日志步骤。
- 显式标出 task 依赖图、可并行任务和 worktree / PR 拆分。

我认为这一步的价值是把“宏观设计”转成了可以交给 subagent 的任务单元，降低正式实现时 agent 自行猜测的空间。

实现开始后，由于我明确要求课程 MVP 而不是完整产品，`PLAN.md` 又被修订了一次：保留 16 个小 task 作为 TDD 和过程证据颗粒度，但把实际 GitHub PR 工作流压缩成 4 个模块 PR。这样既满足“每个 worktree 对应一个 PR”和“每个 task 有 subagent / 测试 / 日志”的要求，又避免把项目做成超出课程时间预算的完整 IDE agent。

## 6. 冷启动验证记录

### 6.1 执行情况

- **冷启动 agent**: deepseek-v4-flash
- **Session 方式**: 未导入前序对话，仅提供 `D:\summerproject\SPEC.md` 和 `D:\summerproject\PLAN.md`
- **要求**: 实现 PLAN.md Task 1，构建于 `D:\summerproject\demo`
- **未完成原有计划**: 只选了 Task 1（未选 Task 2），因为用户明确要求 "根据前两个文件实现 PLAN.md 第一个 task"

### 6.2 暂停与提问记录

**唯一一次暂停**：`make` 命令在 Windows 上不可用。

- PLAN.md Step 5 要求 `make test` 通过退出码 0，但当前 Windows 环境未安装 `make`（PowerShell 中 `Get-Command make` 返回 false）。
- 暂停点：冷启动 agent 在完成 Step 4（测试通过）后，执行 Step 5 前暂停。
- 提问：询问用户是安装 `make` 还是直接用 `python -m pytest` 替代验证。
- 用户回答：用 `python -m pytest` 直接验证。
- 潜在影响：PLAN.md 的 Makefile 目标是正确的（`make test` → `python -m pytest`），问题在于跨平台假设未声明。如果用户将来在 CI 或其他场景依赖 `make`，Windows runner 需要预装 `make` 或改用 PowerShell 脚本。

**没有发生其他暂停**。Task 1 的 Step 1–4 全部顺利通过，无需额外澄清。

### 6.3 暴露的 SPEC / PLAN 缺陷

| 缺陷等级 | 位置 | 描述 |
|---------|------|------|
| 中 | PLAN.md 文件结构 | `pyproject.toml` 仅写 "使用 setuptools" 未指定 build-backend 值。冷启动 agent 初始选择了非标准值 `setuptools.backends._legacy:_Backend`，后自我纠正为标准值 `setuptools.build_meta`。 |
| 低 | PLAN.md Step 5 | `make test` 验证假设 GNU Make 存在。Windows 默认不含 `make`，PLAN 未提供替代验证方式。 |
| 低 | PLAN.md Expected Implementation | 占位 subcommand 的 exit code 未明确。冷启动 agent 返回 1（"not yet implemented" 表示未完成），但也可解释为返回 0（"占位已就绪"）。两种选择无功能影响，但若未来 CI 检查子命令 exit code 可能产生歧义。 |
| 低 | SPEC.md 功能规约 | 第 3.1 节任务入口模块描述未涉及 `--version` 和 `--help` 的输出格式要求。Task 1 测试断言 `"SafeLoop Coding Agent Harness" in result.stdout`，这个字符串在当前实现中由 argparse description 提供，但 SPEC 本身未要求这一确切措辞。 |

### 6.4 解读不一致记录

以下列出冷启动 agent 的解读与主开发 agent 原意的偏差：

**解读一：占位命令 exit code（spec 写得不精确）**

- PLAN.md 说 "占位入口返回清晰错误码和信息，不执行 agent"。
- 冷启动 agent 解读：返回 `1`（错误码），打印 `"demo command: not yet implemented"`。
- 可能的原意：返回 `0` 表示 "占位入口已接通" 或返回非零表示 "无法执行"。
- 归属：**spec 写得不精确**。`PLAN.md` 未规定 placeholder 的明确 exit code 语义。返回 1 在逻辑上说得通（"功能未实现"），但与原意可能不一致的地方是原意可能期望 0（入口可用但实际 agent 未运行）。

**解读二：pyproject.toml build-backend（spec 未写）**

- 冷启动 agent 初始使用了 `setuptools.backends._legacy:_Backend`，这是个历史遗留/非标准值。
- 根源：PLAN.md 只写了 "使用 setuptools"，未提供具体配置节。
- 归属：**spec 写得不精确**。PLAN.md 应该写出 build-backend 的标准值或至少提到 `setuptools.build_meta`。

**解读三：test assertion 中的字符串断言（spec 与 test 一致）**

- 测试断言 `"SafeLoop Coding Agent Harness" in result.stdout` —— 冷启动 agent 完全复制了 PLAN.md 给出的测试代码，未做修改，与原意一致。

### 6.5 产出与预期差距

| 维度 | 预期（PLAN.md） | 实际产出 | 差距 |
|------|---------------|---------|------|
| 测试通过 | 2 passed | 2 passed | 无差距 |
| `python -m safeloop --help` | 显示 SafeLoop 名称、subcommands | 正常显示 | 无差距 |
| `python -m safeloop --version` | 打印 `safeloop <version>` | 打印 `safeloop 0.1.0` | 无差距 |
| `make test` | exits 0 | 未直接验证（环境无 make）；等价命令 `python -m pytest` exits 0 | 差距极小，但跨平台兼容性应改进 |
| 文件结构 | pyproject.toml, Makefile, .gitignore, safeloop/ 包, tests/ | 全部按预期创建 | 无差距 |
| AGENT_LOG.md | 应有 subagent 记录 | 已创建 | 无差距 |
| git commit | "chore(task-1): bootstrap safeloop package" | 未执行（用户未要求 commit） | 无差距（按用户指示跳过） |

**总结差距：很小。** Task 1 的核心产出与 PLAN.md 描述基本一致。主要问题是跨平台 `make` 兼容性和 pyproject.toml build-backend 精确值需要在 PLAN 中明确。

### 6.6 建议的 SPEC / PLAN 修订

以下是根据冷启动验证建议的修订（仅列关键 diff）：

#### 修订 1：`PLAN.md` Task 1 pyproject.toml 增加 build-backend 明确值

```diff
  PLANNED: "pyproject.toml 使用 package name safeloop-agent，Python floor 为 >=3.11。"
  IMPLIED: 使用 setuptools

+ SUGGESTED: pyproject.toml [build-system] 节明确使用
+   [build-system]
+   requires = ["setuptools>=68.0"]
+   build-backend = "setuptools.build_meta"
```

**理由**：避免冷启动 agent 选择非标准 backend。

#### 修订 2：`PLAN.md` Task 1 Step 5 增加跨平台验证说明

```diff
  - [ ] Step 5: Verify one-command test target
    Run: make test
+   If make is unavailable (e.g. Windows), run: python -m pytest
    Expected: Runs python -m pytest and exits 0.
```

**理由**：Windows 不含 GNU Make，PLAN 应提供替代验证方式。

#### 修订 3：`PLAN.md` Task 1 Expected Implementation 明确 placeholder exit code

```diff
  - CLI 使用标准库 argparse，先提供 --version、--help、demo、web、credentials、run
-   子命令占位入口；占位入口返回清晰错误码和信息，不执行 agent。
+   子命令占位入口；占位入口返回 1 并打印 "not yet implemented" 信息，
+   不执行 agent。
```

**理由**：消除 exit code 歧义。

#### 修订 4（可选）：`SPEC.md` 第 3.1 节任务入口模块增加 --help/--version 输出要求

```diff
  行为：校验 workspace，加载配置，创建一次 run，初始化状态和事件日志。
- 输出：run_id、初始 run 状态、配置摘要。
+ 输出：run_id、初始 run 状态、配置摘要。--help 输出项目名称 "SafeLoop Coding Agent Harness"
+ 和子命令列表。--version 输出格式为 "safeloop <version>"。
```

**理由**：使测试断言有规约依据，而非仅依赖 PLAN.md 中的测试代码。

### 6.7 冷启动验证小结

- Task 1 完整可实施：从 SPEC.md 和 PLAN.md 两文档出发，冷启动 agent 可以独立完成 Task 1 的全部步骤。
- 主要不确定点只有 `make` 可用性（跨平台假设）和 pyproject.toml build-backend 精确值。
- 四个建议修订中有两个是 "明确值" 类（build-backend、exit code），一个是 "跨平台替代路径" 类（make），一个是 "规约补充" 类（--help/--version 输出）。
- 没有发现 SPEC.md 的严重缺陷或矛盾，PLAN.md 的细微不精确性通过上述修订即可消除。
- 冷启动验证确认：SPEC.md 和 PLAN.md 的当前质量足够引导后续 task 的独立实施，但建议在正式开发前纳入本节的四个修订。

### 6.8 已采纳的 SPEC / PLAN 修订

根据冷启动反馈，已在正式实现前采纳以下修订：

- `SPEC.md` 第 3.1 节补充 `--help` 和 `--version` 的输出要求，使 Task 1 的 CLI 测试断言有规约依据。
- `PLAN.md` Task 1 明确 `pyproject.toml` 的 build backend 为 `setuptools.build_meta`。
- `PLAN.md` Task 1 明确未实现占位子命令返回 exit code `1` 并打印 `not yet implemented`。
- `PLAN.md` 全局约束和 Task 1 Step 5 补充 Windows 上没有 `make` 时使用 `python -m pytest` 作为替代验证命令。

## 7. 对 Brainstorming 技能的反思

### 7.1 做得好的地方

`brainstorming` 技能强制我先回答“到底要做什么”，而不是一上来写代码。它把项目从“做一个 coding agent”逐步收敛成了“实现一个可测试的 coding agent harness”。这个过程尤其有用，因为 A 项作业真正看重的是 harness 机制，而不是界面或模型效果。

它还促使我质询模糊点。例如用户故事是不是用户的故事、功能规约是否逐模块写五要素、主要贡献到底是什么。这些质询直接提高了 `SPEC.md` 的可评分性。

### 7.2 让我不满或需要人工把关的地方

智能体有时会先给出看起来合理但不完全贴合原文的结构，需要我不断拉回 `general_requirement.md` 的原始条目。例如用户故事一开始容易偏“项目开发者”，而不是 SafeLoop 的真实用户；功能规约也需要我明确要求五要素。

另一个问题是，智能体早期凭据方案把 OS keyring 当成后续扩展，这和通用要求第 3.1 的“至少实现一种安全存储”不完全一致。这个问题是在写 `PLAN.md` 前重新检查作业要求时发现并修正的。

### 7.3 我的经验总结

这次过程让我意识到，Superpowers 的价值不是替我决定项目，而是逼我不断检查“这个决定能不能被文档、测试和交付物证明”。如果我只接受智能体的第一版答案，`SPEC.md` 会更像普通设计文档；经过多轮质询后，它才更像课程要求的规约文件。

本次冷启动验证已经检验了这件事：第二个 agent 只凭 `SPEC.md` 和 `PLAN.md` 能完成 Task 1，但暴露出跨平台验证命令、build backend 和占位命令 exit code 的细节不够明确。把这些细节修订回文档后，后续正式实现的偏航风险更低。
