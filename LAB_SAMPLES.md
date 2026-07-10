# AI4Coding Lab 作业样例：课堂展示 + 课后挑战

这份文档对应 HTML PPT 的 Lab 0-12。样例不是唯一答案，课堂使用时可作为学生提交格式、教师点评和助教检查的参照。

本课程保留两个项目层次：

- **课堂展示项目**：AI for Coding 知识体关联式 HTML 导航器。用于 3 小时实践课现场带做，目标是快速走完 Spec / Checklist / OpenCode / Gate。
- **课后挑战项目**：AI4Coding AgentOS 实验工作台。用于课后练习，目标是让学生在更复杂的多文件、多状态、多证据场景中验证 PE / CE / HE 的必要性。

完整课后挑战需求见 `ADVANCED_LAB_PROJECT.md`。

## A. 课堂展示项目：知识体关联式 HTML 导航器

### 交付目录样例

```text
ai4coding-demo-lab/
  index.html
  opencode.json
  AGENTS.md
  SPEC.md
  CHECKLIST.md
  context-pack.md
  gate-checklist.md
  AGENT_LOG.md
  context-snapshot.md
  mcp-browser-record.md
  prompts/
    stage-template.md
  skills/
    web-stage-check/
      SKILL.md
  hooks/
    pre-commit.sample
  agentpack-draft/
    manifest.yml
    agents/
      checker.yml
```

### 课堂 Lab 提交矩阵

| Lab | 应交产物 | 文件基本内容 | 课堂案例中的角色 |
| --- | --- | --- | --- |
| 0 环境与权限 | `opencode.json`、`AGENTS.md` | OpenCode 权限、模型接入、项目目标、禁止事项、常用检查命令。 | 让 Agent 在可控工作区内读、写、检查。 |
| 1 全局 Spec | `SPEC.md` | 用户、目标、范围、非目标、技术约束、开发阶段。 | 说明要做“知识体关联式 HTML 导航器”。 |
| 2 全局 Checklist | `CHECKLIST.md` | 功能、工程、安全、体验、解释、退出条件。 | 把“能不能完成”写成可观察项。 |
| 3 上下文包 | `context-pack.md` | 当前阶段、必须读、可以读、不得读、输出要求。 | 搜索阶段只给 Agent 看相关项目文件。 |
| 4 阶段 Prompt | `prompts/stage-template.md` | 阶段任务模板、阶段 Spec、阶段 Checklist、约束、计划要求。 | 每次委托 Agent 前先要求计划和检查方式。 |
| 5 MVP | `index.html` 初版 | 节点数据、列表渲染、详情区、基础样式。 | 先让页面能打开、能点击、能展示详情。 |
| 6 搜索与关系 | `index.html` 更新版 | 搜索输入、过滤函数、空状态、`related` 字段、高亮逻辑。 | 增加“搜索 Spec 节点”和“关系高亮”。 |
| 7 Gate 与证据 | `gate-checklist.md` | 当前阶段必过项、证据位置、失败项、退出决定。 | 决定搜索阶段是通过、重试、降级还是停止。 |
| 8 日志与摘要 | `AGENT_LOG.md`、`context-snapshot.md` | 任务、修改、证据、人工决定；下一阶段事实摘要。 | 把搜索阶段结果交接给关系高亮阶段。 |
| 9 MCP | `mcp-browser-record.md` | 浏览器观察步骤、Console / DOM / Network 证据、回灌内容。 | 手动模拟 MCP，把浏览器现象变成 Agent 可用证据。 |
| 10 Skill | `skills/web-stage-check/SKILL.md` | 触发条件、检查步骤、输入文件、输出格式、禁止事项。 | 把 Web 阶段检查沉淀为可复用套路。 |
| 11 Hook | `hooks/pre-commit.sample` | 密钥扫描、Gate 文件检查、提交前提醒。 | 用确定性脚本守住提交边界。 |
| 12 LambdAgentPaaS | `agentpack-draft/manifest.yml`、`agentpack-draft/agents/checker.yml` | AgentPack 元数据、权限、模型建议、检查 Agent 定义。 | 把课堂检查 Agent 设计成可部署、可追踪资产。 |

### 课堂贯穿案例：搜索 Spec 节点

1. `SPEC.md`：写明“学生输入关键词后，只显示标题、定义、检查点中匹配的知识体节点”。
2. `CHECKLIST.md`：写明“搜 Spec 有结果、搜不存在词有空状态、清空恢复全部、详情点击不坏”。
3. `context-pack.md`：写明本阶段只读取 `index.html`、`SPEC.md`、`CHECKLIST.md`、`AGENTS.md`。
4. `prompts/stage-template.md`：要求 Agent 先列计划、涉及函数、风险和检查步骤。
5. `index.html`：新增 `searchInput`、`filterNodes`、`renderNodes(filtered)`，不重写节点数据。
6. `gate-checklist.md`：逐项检查搜索行为，并记录是否进入下一阶段。
7. `AGENT_LOG.md`：记录 OpenCode 的修改、检查证据和人工放行决定。
8. `context-snapshot.md`：写清“搜索已通过；下一阶段只做 related 高亮，不再讨论搜索交互”。

## B. 课后挑战项目：AI4Coding AgentOS 实验工作台

课后挑战项目不是替换课堂 Lab，而是复用 Lab 1-12 的方法，在更复杂的需求上再次练习。

### 总体交付目录样例

```text
ai4coding-agentos-lab/
  index.html
  opencode.json
  AGENTS.md
  SPEC.md
  CHECKLIST.md
  context-pack.md
  gate-checklist.md
  AGENT_LOG.md
  context-snapshot.md
  mcp-browser-record.md
  assets/
    styles.css
    app.js
  data/
    concepts.js
    labs.js
    stages.js
    policies.js
  prompts/
    stage-template.md
  skills/
    lab-stage-check/
      SKILL.md
  hooks/
    pre-commit.sample
  agentpack-draft/
    manifest.yml
    agents/
      gate-checker.yml
```

## Lab 提交矩阵

| Lab | 应交产物 | 文件基本内容 | 案例讲解中的角色 |
| --- | --- | --- | --- |
| 0 环境与权限 | `opencode.json`、`AGENTS.md` | OpenCode 权限、模型接入、项目目标、禁止事项、常用检查命令。 | 让 Agent 只能在可控工作区内读、写、检查。 |
| 1 全局 Spec | `SPEC.md` | 用户、目标、范围、非目标、模块、数据模型、开发阶段。 | 说明要做“AgentOS 实验工作台”。 |
| 2 全局 Checklist | `CHECKLIST.md` | 功能、状态、证据、安全、体验、解释、退出条件。 | 把“Lab 能不能 pass”写成可观察项。 |
| 3 上下文包 | `context-pack.md` | 当前阶段、必须读、可以读、不得读、输出要求。 | Lab 看板阶段只给 Agent 看相关数据与实现文件。 |
| 4 阶段 Prompt | `prompts/stage-template.md` | 阶段任务模板、阶段 Spec、阶段 Checklist、约束、计划要求。 | 每次委托 Agent 前先要求计划和检查方式。 |
| 5 MVP | `index.html`、`assets/*`、`data/*.js` | 概念图谱、Lab 看板、阶段合同、权限风险面板静态展示。 | 先让工作台能打开、能切换视图、能展示数据。 |
| 6 状态与 Gate 证据 | `assets/app.js` 更新版 | Lab 状态切换、Gate 证据记录、`localStorage` 持久化。 | 增加“无证据不能 pass”的 Gate 规则。 |
| 7 Gate 与证据 | `gate-checklist.md` | 当前阶段必过项、证据位置、失败项、退出决定。 | 决定 Gate 阶段是通过、重试、降级还是停止。 |
| 8 日志与摘要 | `AGENT_LOG.md`、`context-snapshot.md` | 任务、修改、证据、人工决定；下一阶段事实摘要。 | 把 Gate 阶段结果交接给证据导出或选做扩展阶段。 |
| 9 MCP | `mcp-browser-record.md` | 浏览器观察步骤、Console / DOM / localStorage 证据、回灌内容。 | 手动模拟 MCP，把页面状态变成 Agent 可用证据。 |
| 10 Skill | `skills/lab-stage-check/SKILL.md` | 触发条件、检查步骤、输入文件、输出格式、禁止事项。 | 把 Lab 阶段检查沉淀为可复用套路。 |
| 11 Hook | `hooks/pre-commit.sample` | 密钥扫描、Gate 文件检查、JS 语法检查。 | 用确定性脚本守住提交边界。 |
| 12 LambdAgentPaaS | `agentpack-draft/manifest.yml`、`agentpack-draft/agents/gate-checker.yml` | AgentPack 元数据、权限、模型建议、GateChecker Agent 定义。 | 把 Gate 检查 Agent 设计成可部署、可追踪资产。 |

## 贯穿案例：Lab 有 Gate 证据后才能 pass

本案例贯穿 Lab 1-8，展示一个功能切片如何从需求走到验收。

1. `SPEC.md`：写明“Lab 没有 Gate 证据时不能标记为 pass；有证据后可以放行”。
2. `CHECKLIST.md`：写明“可添加证据、无证据禁 pass、有证据可 pass、刷新后状态和证据保持”。
3. `context-pack.md`：写明本阶段只读取 `data/labs.js`、`assets/app.js`、`SPEC.md`、`CHECKLIST.md`、`AGENTS.md`。
4. `prompts/stage-template.md`：要求 Agent 先列状态模型、涉及函数、风险和检查步骤。
5. `assets/app.js`：新增 `evidenceRecords`、`canPassLab`、`saveState`、`loadState`，不重写概念图谱。
6. `gate-checklist.md`：逐项检查证据新增、pass 限制、刷新持久化，并记录是否进入下一阶段。
7. `AGENT_LOG.md`：记录 OpenCode 的修改、检查证据和人工放行决定。
8. `context-snapshot.md`：写清“Gate 证据已通过；下一阶段只做证据导出，不再重做状态模型”。

## Lab 0：环境与权限

**应交物**：`opencode.json`、`AGENTS.md`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "*": "ask",
    "read": {
      "*": "allow",
      "*.env": "deny",
      "*.env.*": "deny",
      "*.env.example": "allow"
    },
    "edit": { "*": "ask" },
    "bash": {
      "*": "ask",
      "pwd": "allow",
      "ls*": "allow",
      "rg*": "allow",
      "git status*": "allow",
      "node --check*": "allow",
      "npm test*": "allow",
      "npm run build*": "allow",
      "rm *": "deny",
      "git push --force*": "deny"
    },
    "webfetch": "deny"
  }
}
```

```markdown
# AGENTS.md

## 项目目标

构建 AI4Coding AgentOS 实验工作台。

## 优先阅读

- SPEC.md
- CHECKLIST.md
- context-pack.md
- AGENT_LOG.md
- data/labs.js
- assets/app.js

## 常用检查

- 打开 index.html
- 检查浏览器 Console
- 测试 Lab 状态切换
- 测试 Gate 证据记录
- 刷新后检查 localStorage 持久化
- 检查窄屏显示

## 禁止事项

- 不读取 .env
- 不引入未知外部脚本
- 不执行部署和远程写操作
- 不删除已有 Lab 产物
```

## Lab 1：写全局 Spec

**应交物**：`SPEC.md`

```markdown
# SPEC.md

## 项目目标

做一个可以本地打开的 AI4Coding AgentOS 实验工作台，用来展示 AgentOS 概念、Lab 0-12 作业、阶段合同、Gate 证据和权限风险。

## 用户

- 夏令营学生：按阶段完成 Lab，记录 Gate 证据，理解 PE / CE / HE 的作用。
- 任课教师 / 助教：检查学生是否写清 Spec、Checklist、context-pack、Gate 证据和日志。

## 核心模块

1. 概念图谱：展示 AgentOS 五层和核心概念。
2. Lab 看板：展示 Lab 0-12、应交物、状态和关联知识点。
3. 阶段合同：展示每个阶段的目标、输入、禁止事项、Checklist 和退出条件。
4. Gate 证据：给每个 Lab 添加证据记录；无证据不能标记 pass。
5. 权限风险：展示 allow / ask / deny 的课堂默认策略。

## 不做事项

- 不接真实模型 API。
- 不做用户登录。
- 不接后端数据库。
- 不做复杂拖拽和大型动画。

## 技术约束

- 静态 HTML / CSS / JavaScript。
- 可以多文件组织：`assets/` 与 `data/`。
- 不依赖网络资源。
- 状态保存在 `localStorage`。
- API Key 不得写入任何文件。

## 阶段划分

1. MVP：概念图谱 + Lab 看板 + 阶段合同静态展示。
2. 状态：Lab 状态切换并保存。
3. Gate：证据记录与 pass 限制。
4. 检查：Console、窄屏、刷新持久化。
5. 日志与摘要：记录过程，写阶段快照。
6. 进阶：MCP、Skill、Hook、LambdAgentPaaS 四选一。
```

## Lab 2：写全局 Checklist

**应交物**：`CHECKLIST.md`

```markdown
# CHECKLIST.md

## 功能检查

- [ ] 页面能直接打开 index.html。
- [ ] 能看到 AgentOS 概念图谱。
- [ ] 能看到 Lab 0-12 看板。
- [ ] 每个 Lab 显示应交文件、关联知识点、通过标志。
- [ ] Lab 状态可以在 todo / doing / blocked / pass 间切换。
- [ ] 没有 Gate 证据时不能标记 pass。
- [ ] 添加 Gate 证据后可以标记 pass。
- [ ] 刷新页面后状态和证据仍然存在。
- [ ] 能看到权限风险面板。

## 工程检查

- [ ] 概念、Lab、阶段、权限数据分文件管理。
- [ ] 渲染、状态、证据、过滤等函数边界清楚。
- [ ] 命名能看出用途。
- [ ] 没有大段重复代码。

## 安全检查

- [ ] 没有 API Key。
- [ ] 没有未知远程脚本。
- [ ] 没有删除文件、联网部署、付费调用等高风险动作。

## 退出条件

- [ ] 所有必选项通过，进入下一阶段。
- [ ] 有失败项，回到修复。
- [ ] 连续两轮失败，缩小范围或人工接管。
```

## Lab 3：上下文包

**应交物**：`context-pack.md`

```markdown
# context-pack.md

## 当前阶段

Lab 看板 MVP：生成概念图谱、Lab 看板和阶段合同静态展示。

## 必须读取

- SPEC.md
- CHECKLIST.md
- AGENTS.md
- data/concepts.js
- data/labs.js
- data/stages.js
- assets/app.js

## 可以读取

- 设计草图或截图
- 上一阶段 context-snapshot.md

## 不得读取

- .env
- API Key
- 无关历史对话
- 旧版本完整 Lecture

## 输出要求

先给计划，列出涉及文件、状态模型、风险、检查步骤。等我确认后再修改文件。
```

## Lab 4：阶段 Prompt

**应交物**：`prompts/stage-template.md`

```markdown
你是本项目的前端实现助手。
请阅读 @SPEC.md @CHECKLIST.md @AGENTS.md @context-pack.md。

当前阶段：[阶段名]

阶段 Spec：
- [只做什么]

阶段 Checklist：
- [如何判断通过]

约束：
- 不重写全项目
- 不引入外部依赖
- 不读取 .env
- 不修改与本阶段无关的数据结构

请先给计划：步骤、涉及文件、状态模型、风险、检查方式。
等我确认后再修改文件。
```

## Lab 5：生成 MVP

**应交物**：`index.html`、`assets/styles.css`、`assets/app.js`、`data/*.js`

MVP 至少包括：

- AgentOS 概念图谱静态展示。
- Lab 0-12 看板静态展示。
- 阶段合同面板静态展示。
- 权限风险面板静态展示。
- 基本视图切换。
- 无 Console 红色错误。

## Lab 6：状态与 Gate 证据

**应交物**：更新后的 `assets/app.js`

状态阶段验收：

- [ ] Lab 状态可以在 `todo`、`doing`、`blocked`、`pass` 间切换。
- [ ] 状态写入 `localStorage`。
- [ ] 刷新后状态保持。
- [ ] 不影响概念图谱和阶段合同展示。

Gate 证据阶段验收：

- [ ] 每个 Lab 可添加证据记录。
- [ ] 证据包含类型、检查方式、结果、人工决定。
- [ ] 无证据时不能标记 `pass`。
- [ ] 有证据后可以标记 `pass`。
- [ ] 刷新后证据仍然存在。

## Lab 7：Gate 与证据

**应交物**：`gate-checklist.md`

```markdown
# gate-checklist.md

## 当前阶段：Gate 证据

### 必须通过

- [ ] Lab 状态可以在 todo / doing / blocked 间切换。
- [ ] 没有证据时不能标记 pass。
- [ ] 添加证据后可以标记 pass。
- [ ] 刷新页面后状态和证据仍然存在。
- [ ] Console 无红色错误。
- [ ] 窄屏下文字不重叠。

### 证据位置

- 截图：evidence/lab-gate-pass.png
- Console：AGENT_LOG.md 当前阶段记录
- localStorage：mcp-browser-record.md 或人工记录

### 退出决定

- [ ] 通过，进入日志与摘要阶段。
- [ ] 未通过，回到修复。
- [ ] 范围过大，降级为只记录一条证据。
```

## Lab 8：日志与摘要

**应交物**：`AGENT_LOG.md`、`context-snapshot.md`

```markdown
# AGENT_LOG.md

## 2026-07-07 Lab 6 Gate 证据

- 我给 OpenCode 的任务：只增加 Lab 状态与 Gate 证据，不改概念图谱。
- OpenCode 修改：assets/app.js 中新增状态保存、证据记录、pass 限制。
- 检查证据：
  - 无证据时 pass 被阻止。
  - 添加证据后可以 pass。
  - 刷新后状态和证据保持。
- 人工决定：通过，进入日志与摘要阶段。
```

```markdown
# context-snapshot.md

## 已完成

- Lab 看板状态切换已完成。
- Gate 证据记录已完成。
- 无证据不能 pass 的规则已通过 Gate。

## 下一阶段

- 只做证据导出或选做扩展。
- 不再重做状态模型。
- 不修改概念图谱数据结构。
```

## Lab 9：MCP 实验

**应交物**：`mcp-browser-record.md`

```markdown
# mcp-browser-record.md

## 检查目标

验证 Lab 状态和 Gate 证据是否真实保存在浏览器状态中。

## 手动模拟 MCP 步骤

1. 打开 index.html。
2. 将 Lab 6 状态改为 doing。
3. 尝试无证据标记 pass，记录失败提示。
4. 添加一条 Gate 证据。
5. 标记 pass。
6. 刷新页面。
7. 记录 Lab 6 状态和证据是否保持。

## 回灌给 Agent 的证据

- Console 是否有错误。
- localStorage 中是否有 lab 状态和 evidence 记录。
- 页面是否显示 pass。
```

## Lab 10：Skill 实验

**应交物**：`skills/lab-stage-check/SKILL.md`

```markdown
---
name: lab-stage-check
description: 当用户要求检查 AgentOS 实验工作台阶段作业时使用
---

## 步骤

1. 阅读 CHECKLIST.md 和 gate-checklist.md。
2. 检查页面加载和 Console。
3. 检查 Lab 状态切换。
4. 检查 Gate 证据与 pass 限制。
5. 刷新页面，检查 localStorage 持久化。
6. 检查窄屏显示。
7. 输出通过项、失败项、证据、建议。

## 约束

不要修改代码，只输出检查报告。
```

## Lab 11：Hook 实验

**应交物**：`hooks/pre-commit.sample`

```bash
#!/usr/bin/env bash
set -e

if rg "sk-[A-Za-z0-9]" . --glob '!/.git/**'; then
  echo "疑似 API Key，禁止提交"
  exit 1
fi

test -f gate-checklist.md || {
  echo "缺少 gate-checklist.md"
  exit 1
}

node --check assets/app.js
for f in data/*.js; do
  node --check "$f"
done
```

## Lab 12：LambdAgentPaaS / AgentPack 扩展

**应交物**：`agentpack-draft/manifest.yml`、`agentpack-draft/agents/gate-checker.yml`

```yaml
id: course.gate-checker
name: Lab Gate Checker
version: 0.1.0
entrypoint: agents/gate-checker.yml
permissions:
  network: false
  shell: false
  file_write: workspace
  read_knowledge: true
description: >
  根据 Spec / Checklist / Gate 证据检查 Lab 状态，
  输出通过项、失败项和退出建议。
```

```yaml
agentId: gate-checker
system: |
  你是 AI4Coding AgentOS 实验工作台的 Gate 检查 Agent。
  你必须读取 SPEC.md、CHECKLIST.md、gate-checklist.md、AGENT_LOG.md。
  你只输出检查报告，不直接修改代码。
maxSteps: 6
outputs:
  - passed_items
  - failed_items
  - missing_evidence
  - exit_recommendation
```
