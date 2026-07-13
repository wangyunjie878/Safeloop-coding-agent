from __future__ import annotations

import argparse
from collections.abc import Sequence
import getpass
from pathlib import Path
import sys

from . import __version__
from .config import default_config_for_workspace, load_config
from .credentials import CredentialError, CredentialManager
from .demo import print_chat_summary, print_run_summary, run_demo, run_harness, run_harness_with_config
from .llm.deepseek import DeepSeekClient
from .models import HarnessConfig


_DEFAULT_MOCK_FINISH_RESPONSE = (
    '{"tool_name":"finish","arguments":{"message":"mock run complete"},'
    '"reason":"default mock response","expected_outcome":"stop"}'
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safeloop",
        description="SafeLoop Coding Agent Harness",
    )
    parser.add_argument("--version", action="version", version=f"safeloop {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run the deterministic mechanism demo")
    demo_parser.set_defaults(command="demo")

    web_parser = subparsers.add_parser("web", help="Run the SafeLoop FastAPI WebUI")
    web_parser.set_defaults(command="web")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8000)

    run_parser = subparsers.add_parser("run", help="Run a task from a SafeLoop config")
    run_parser.set_defaults(command="run")
    run_parser.add_argument("--config")
    run_parser.add_argument("--workspace")
    run_parser.add_argument("--task", required=True)
    run_parser.add_argument("--llm", choices=("mock", "deepseek"))
    run_parser.add_argument("--model")
    run_parser.add_argument("--credential-backend", choices=("keyring", "env", "dotenv"))
    run_parser.add_argument("--dotenv-path")
    run_parser.add_argument("--mock-response", action="append", default=[])

    chat_parser = subparsers.add_parser("chat", help="Chat with SafeLoop in the terminal")
    chat_parser.set_defaults(command="chat")
    chat_parser.add_argument("--config")
    chat_parser.add_argument("--workspace")
    chat_parser.add_argument("--llm", choices=("mock", "deepseek"))
    chat_parser.add_argument("--model")
    chat_parser.add_argument("--credential-backend", choices=("keyring", "env", "dotenv"))
    chat_parser.add_argument("--dotenv-path")
    chat_parser.add_argument("--mock-response", action="append", default=[])

    credentials_parser = subparsers.add_parser("credentials", help="Manage provider credentials")
    credentials_parser.set_defaults(command="credentials")
    credentials_subparsers = credentials_parser.add_subparsers(dest="credentials_command", required=True)
    backend_parent = argparse.ArgumentParser(add_help=False)
    backend_parent.add_argument("--backend", choices=("keyring", "env", "dotenv"), default="keyring")
    backend_parent.add_argument("--dotenv-path")

    for name in ("status", "set", "clear"):
        subparser = credentials_subparsers.add_parser(
            name,
            help=f"{name} stored credentials",
            parents=[backend_parent],
        )
        subparser.add_argument("--provider", required=True)

    return parser


def _placeholder_command(name: str) -> int:
    print(f"{name} is not yet implemented.")
    return 1


def _run_command(args: argparse.Namespace) -> int:
    config = _resolve_runtime_config(args)
    llm_provider = config.llm_provider
    if llm_provider == "deepseek":
        llm_client = _build_deepseek_client(config, args)
        if llm_client is None:
            return 1
        run, events = run_harness_with_config(args.task, config, llm_client)
        print_run_summary(run, events)
        return 0 if run.status == "finished" else 1

    mock_responses = list(args.mock_response) or [_DEFAULT_MOCK_FINISH_RESPONSE]
    if args.config:
        run, events = run_harness(args.task, Path(args.config), mock_responses)
    else:
        from .llm.mock import MockLLMClient

        run, events = run_harness_with_config(args.task, config, MockLLMClient(mock_responses))
    print_run_summary(run, events)
    return 0 if run.status == "finished" else 1


def _resolve_runtime_config(args: argparse.Namespace) -> HarnessConfig:
    if args.config:
        config = load_config(Path(args.config))
    else:
        workspace = Path(args.workspace) if args.workspace else Path.cwd()
        config = default_config_for_workspace(workspace, llm_provider=args.llm or "mock")

    if args.llm and args.llm != config.llm_provider:
        config = config.model_copy(update={"llm_provider": args.llm})
    return config


def _build_deepseek_client(config: HarnessConfig, args: argparse.Namespace) -> DeepSeekClient | None:
    backend = args.credential_backend or config.credential_backend
    manager = CredentialManager(backend=backend, dotenv_path=args.dotenv_path)
    try:
        api_key = manager.get_key("deepseek")
    except CredentialError as exc:
        print(f"credential error: {exc}", file=sys.stderr)
        return None
    if not api_key:
        source = "DEEPSEEK_API_KEY" if backend in {"env", "dotenv"} else "safeloop credentials set --provider deepseek"
        print(f"missing DeepSeek API key; configure {source}", file=sys.stderr)
        return None

    model = args.model or config.model or "deepseek-v4-flash"
    return DeepSeekClient(api_key=api_key, model=model)


def _run_chat_command(args: argparse.Namespace) -> int:
    config = _resolve_runtime_config(args)
    llm_provider = config.llm_provider
    print("SafeLoop CLI 对话模式")
    print("输入 exit 或 quit 退出。任务运行时按 Ctrl+C 只终止当前任务。")

    while True:
        try:
            task = input("safeloop> ").strip()
        except EOFError:
            print()
            return 0

        if task.lower() in {"exit", "quit"}:
            return 0
        if not task:
            continue

        print("正在执行任务，按 Ctrl+C 可终止当前任务...")
        try:
            if llm_provider == "deepseek":
                llm_client = _build_deepseek_client(config, args)
                if llm_client is None:
                    return 1
                run, events = run_harness_with_config(task, config, llm_client)
            else:
                mock_responses = list(args.mock_response) or [_DEFAULT_MOCK_FINISH_RESPONSE]
                if args.config:
                    run, events = run_harness(task, Path(args.config), mock_responses)
                else:
                    from .llm.mock import MockLLMClient

                    run, events = run_harness_with_config(task, config, MockLLMClient(mock_responses))
        except KeyboardInterrupt:
            print()
            print("已终止当前任务，SafeLoop 仍在运行。")
            continue
        print_chat_summary(run, events)


def _run_web_command(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("safeloop.web:create_app", host=args.host, port=args.port, factory=True)
    return 0


def _run_credentials_command(args: argparse.Namespace) -> int:
    manager = CredentialManager(backend=args.backend, dotenv_path=args.dotenv_path)

    if args.credentials_command == "status":
        print(manager.status(args.provider)["status"])
        return 0
    if args.credentials_command == "set":
        key = getpass.getpass("API key: ")
        manager.set_key(args.provider, key)
        print("configured")
        return 0
    if args.credentials_command == "clear":
        manager.clear_key(args.provider)
        print("missing")
        return 0
    raise ValueError(f"Unknown credentials command: {args.credentials_command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        return 0

    if args.command == "credentials":
        return _run_credentials_command(args)
    if args.command == "demo":
        return run_demo()
    if args.command == "chat":
        return _run_chat_command(args)
    if args.command == "run":
        return _run_command(args)
    if args.command == "web":
        return _run_web_command(args)

    return _placeholder_command(args.command)

