from __future__ import annotations

import argparse
import re
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from newsletter.digest import (
    generate_digest,
    get_now,
    get_output_path,
    inspect_digest,
    log,
)


def get_cli_version() -> str:
    try:
        return package_version("newsletter")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        try:
            pyproject_text = pyproject_path.read_text(encoding="utf-8")
        except OSError:
            return "unknown"

        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
        return match.group(1) if match else "unknown"


def command_generate(_: argparse.Namespace) -> int:
    return generate_digest()


def command_status(_: argparse.Namespace) -> int:
    now = get_now()
    output_path = get_output_path(now)
    inspection = inspect_digest(output_path, now)

    print(f"status: {inspection.state}")
    print(f"path: {output_path}")
    print(f"detail: {inspection.detail}")

    return 0 if inspection.state in {"success", "partial"} else 1


def command_show(_: argparse.Namespace) -> int:
    output_path = get_output_path()
    if not output_path.exists():
        log("ERROR", f"Digest file does not exist: {output_path}")
        return 1

    try:
        print(output_path.read_text(encoding="utf-8"), end="")
    except OSError as exc:
        log("ERROR", f"Failed to read digest file: {exc}")
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newsletter",
        description="Generate and inspect the daily tech digest.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show version information and exit",
    )
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate today's digest.",
        description="Fetch GitHub Trending and Hacker News and write today's digest.",
    )
    generate_parser.set_defaults(handler=command_generate)

    status_parser = subparsers.add_parser(
        "status",
        help="Check today's digest status.",
        description="Report whether today's digest exists and whether it looks complete.",
    )
    status_parser.set_defaults(handler=command_status)

    show_parser = subparsers.add_parser(
        "show",
        help="Print today's digest.",
        description="Print today's digest Markdown file to stdout.",
    )
    show_parser.set_defaults(handler=command_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        print(f"{parser.prog} {get_cli_version()}")
        return 0

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return handler(args)
