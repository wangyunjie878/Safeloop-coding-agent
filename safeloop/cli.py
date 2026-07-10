from __future__ import annotations

import argparse
from collections.abc import Sequence
import getpass

from . import __version__
from .credentials import CredentialManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safeloop",
        description="SafeLoop Coding Agent Harness",
    )
    parser.add_argument("--version", action="version", version=f"safeloop {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    for name in ("demo", "web", "run"):
        command_parser = subparsers.add_parser(name, help=f"{name} command placeholder")
        command_parser.set_defaults(command=name)

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

    return _placeholder_command(args.command)

