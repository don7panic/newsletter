from __future__ import annotations

import argparse
import logging
import re
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from newsletter.digest import (
    generate_digest,
    get_now,
    get_output_path,
    inspect_digest,
)
from newsletter.logging_config import configure_logging

LOGGER = logging.getLogger(__name__)


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
        LOGGER.error("Newsletter file does not exist: %s", output_path)
        return 1

    try:
        print(output_path.read_text(encoding="utf-8"), end="")
    except OSError as exc:
        LOGGER.error("Failed to read newsletter file: %s", exc)
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newsletter",
        description="Generate and inspect the daily tech newsletter.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show version information and exit",
    )
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate today's newsletter.",
        description="Fetch GitHub Trending and Hacker News and write today's newsletter.",
    )
    generate_parser.set_defaults(handler=command_generate)

    status_parser = subparsers.add_parser(
        "status",
        help="Check today's newsletter status.",
        description="Report whether today's newsletter exists and whether it looks complete.",
    )
    status_parser.set_defaults(handler=command_status)

    show_parser = subparsers.add_parser(
        "show",
        help="Print today's newsletter.",
        description="Print today's newsletter Markdown file to stdout.",
    )
    show_parser.set_defaults(handler=command_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
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
