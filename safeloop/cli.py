from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safeloop",
        description="SafeLoop Coding Agent Harness",
    )
    parser.add_argument("--version", action="version", version=f"safeloop {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    for name in ("demo", "web", "credentials", "run"):
        command_parser = subparsers.add_parser(name, help=f"{name} command placeholder")
        command_parser.set_defaults(command=name)

    return parser


def _placeholder_command(name: str) -> int:
    print(f"{name} is not yet implemented.")
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        return 0

    return _placeholder_command(args.command)

