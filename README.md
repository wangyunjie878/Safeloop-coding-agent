# SafeLoop

## 项目简介 / Project Overview

SafeLoop 是一个轻量级 Coding Agent Harness。它面向本地代码开发者，可以在用户指定的工作目录中读取文件、写入或修改代码、执行命令、运行测试，并根据工具结果或测试失败继续调整下一步行动。

项目默认提供 deterministic mock LLM，用于离线机制演示、单元测试和 CI。真实模型接入是可选能力，目前支持用户自带 DeepSeek API key；仓库不会保存任何真实凭据。

## 安装 / Installation

前提：本机需要 Python 3.11 或更新版本。

SafeLoop 是本地 Python CLI。普通使用安装：

```bash
python -m pip install -e .
```

开发或跑测试安装：

```bash
python -m pip install -e ".[dev]"
```

这里的 `-e` 表示 editable install，也就是修改源码后不需要反复重新安装。普通用户只运行 CLI 时用 `python -m pip install -e .`；如果要运行 `pytest`、开发或检查作业测试，再用 `python -m pip install -e ".[dev]"`。

## 运行 / Running

下面是从零开始的完整使用流程。

### 1. 获取源码 / 获取方式

从 GitHub 拉取项目：

```bash
git clone https://github.com/wangyunjie878/Safeloop-coding-agent.git
cd Safeloop-coding-agent
```

也可以直接下载 GitHub ZIP 包，解压后进入 `Safeloop-coding-agent` 文件夹。

### 2. 安装 SafeLoop

普通使用安装：

```bash
python -m pip install -e .
```

如果你要运行测试或继续开发，用开发安装：

```bash
python -m pip install -e ".[dev]"
```

### 3. 配置 DeepSeek API key

运行：

```bash
python -m safeloop credentials set --provider deepseek
```

终端会提示你输入 DeepSeek API key。粘贴时终端不会显示你粘贴的 key，这是正常的安全行为；粘贴完成后直接按回车即可。SafeLoop 会把 key 写入系统 keyring，之后再次启动通常不需要重复输入。

### 4. 选择要操作的代码目录

进入你要让 agent 操作的代码目录，也就是你希望它读写文件、执行命令、运行测试的那个文件夹：

```bash
cd path/to/your/project
```

Windows 示例：

```powershell
cd "D:\new code"
```

### 5. 启动对话式 agent

在你的代码目录里运行：

```bash
python -m safeloop chat --llm deepseek
```

启动后可以直接输入自然语言任务：

```text
帮我写一个统计 1 到 100 质数个数的 Python 程序
解释这个项目的测试怎么运行
帮我修复当前目录里的 failing tests
```

`chat` 默认把当前目录当作 workspace。也可以用 `--workspace path/to/project` 指向其他目录：

```bash
python -m safeloop chat --workspace path/to/your/project --llm deepseek
```

对话模式默认输出中文用户反馈。任务运行时按 `Ctrl+C` 只会终止当前任务，并回到 `safeloop>` 提示符；输入 `exit` 或 `quit` 才会退出 SafeLoop。

如果需要项目级配置，例如自定义测试命令、阻止某些危险命令、调整超时或默认模型，可以在你的代码项目中放 `safeloop.yml`，然后启动时指定它：

```bash
python -m safeloop chat --config safeloop.yml --llm deepseek
```

## 机制演示

机制演示用于给老师展示 mock LLM、护栏拦截、测试失败反馈和自动修正闭环，不是普通用户日常使用方式。它不需要真实 API key。

建议在 SafeLoop 仓库根目录执行，也就是包含 `README.md`、`safeloop/` 和 `samples/` 的目录：

```bash
cd path/to/Safeloop-coding-agent
python -m safeloop demo
```

如果要运行样例 workspace，也在 SafeLoop 仓库根目录执行，因为命令里的 `samples/...` 是相对路径：

```bash
python -m safeloop run --config samples/python_buggy_calculator/safeloop.yml --task "fix calculator" --llm mock
```

## Key 安全配置 / Credential Security

真实 LLM key 由使用者自己提供，仓库内不包含任何真实凭据。推荐使用运行教程第 3 步，把 DeepSeek key 写入操作系统 keyring：

```bash
python -m safeloop credentials set --provider deepseek
```

粘贴 key 时终端不显示字符是正常现象，不代表没有输入；粘贴后按回车即可保存。

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

## 目录结构 / Directory Structure

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

## 安全边界说明 / Safety Boundaries

SafeLoop 的工具执行受 workspace 限制：文件读取、写入、patch 和命令执行默认只能发生在用户选择的工作目录中。路径逃逸、敏感文件、危险命令和超时命令会被拒绝或反馈给 agent。项目还会对事件日志、反馈和 provider 上下文中的已知 secret 做脱敏处理。

需要注意的是，SafeLoop 是教学型 harness，不是完整沙箱或权限隔离系统。它能减少误操作风险，但不能替代操作系统权限、容器隔离、代码审查或真实生产环境的安全策略。

## 测试 / Testing

一键测试命令：

```bash
make test
```

Windows 上如果没有 GNU Make，可以使用等价命令：

```bash
python -m pytest -q
```

本项目的核心机制测试使用 mock/stub LLM，不依赖网络，也不会调用真实 DeepSeek。测试覆盖主循环、工具分发、护栏拦截、反馈闭环、凭据脱敏、CLI 和分发配置。

## CI/CD

GitHub Actions 配置文件位于 `.github/workflows/ci.yml`。每次 push 和 pull request 都会自动运行，包括只改文档的提交。

CI 会执行：

```text
python -m pytest -q
python -m safeloop demo
docker build -t safeloop-agent .
```

GitLab CI 兼容配置位于 `.gitlab-ci.yml`，其中包含作业要求里的 `unit-test` job，并运行 `python -m pytest -q`。

## 分发命令 / Distribution

SafeLoop 的主要使用入口是本地 Python CLI：下载安装到本机后，进入目标代码目录运行 `python -m safeloop chat --llm deepseek`。

Docker 不是日常 CLI 使用的主入口；它主要用于分发配置展示、WebUI smoke test 和 CI 中证明镜像可以构建。需要容器演示时可以运行：

```bash
docker build -t safeloop-agent .
docker run --rm -p 8000:8000 safeloop-agent
```

容器启动后会运行 WebUI，监听 `0.0.0.0:8000`，默认使用 mock LLM，不需要真实 API key。

## 已知限制 / Known Limits

- `chat` 是简化版 CLI，不是完整 opencode/Codex 复刻；每次用户输入会启动一个有步数上限的 harness run。
- WebUI 主要用于展示和 API smoke test，功能比 CLI 少。
- Docker 镜像默认运行 mock WebUI，不内置真实 LLM key。
- DeepSeek 调用依赖用户自己的 key 和网络环境；CI 不会调用真实 DeepSeek。
- Windows 本地如果没有 GNU Make，请使用 `python -m pytest -q` 替代 `make test`。
