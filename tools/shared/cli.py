"""Shared command-line helpers for the BTicino maintenance tools."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
from pathlib import Path
import sys


_LOGGER = logging.getLogger("bticino_tools")


@dataclass(frozen=True)
class ToolOptions:
    """Options shared by the maintenance tools."""

    config_path: Path
    dry_run: bool = False
    verbose: bool = False
    backup: bool = True
    assume_yes: bool = False


def build_parser(
    description: str,
    *,
    include_write_options: bool = True,
) -> argparse.ArgumentParser:
    """Build an argument parser with the shared options.

    ``include_write_options`` adds the flags that only make sense for tools that
    modify files (``--dry-run``, ``--no-backup``, ``--yes``); read-only tools
    can omit them.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config",
        default="/config",
        help=(
            "Home Assistant config directory, or an offline copy that contains "
            "a .storage folder (default: /config)"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print more detailed output",
    )

    if include_write_options:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without modifying any file",
        )
        parser.add_argument(
            "--no-backup",
            action="store_true",
            help="Do not create a backup before modifying a file (not recommended)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Do not ask for confirmation before modifying a file",
        )

    return parser


def parse_options(parser: argparse.ArgumentParser) -> ToolOptions:
    """Parse arguments into :class:`ToolOptions` and validate the config path."""
    args = parser.parse_args()
    config_path = Path(args.config).expanduser()

    if not config_path.is_dir():
        parser.error(f"Config path is not a directory: {config_path}")

    configure_logging(args.verbose)

    return ToolOptions(
        config_path=config_path,
        dry_run=getattr(args, "dry_run", False),
        verbose=args.verbose,
        backup=not getattr(args, "no_backup", False),
        assume_yes=getattr(args, "yes", False),
    )


def configure_logging(verbose: bool) -> None:
    """Configure logging output for the tools."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        force=True,
    )


def get_logger() -> logging.Logger:
    """Return the shared tools logger."""
    return _LOGGER


def confirm(question: str, assume_yes: bool) -> bool:
    """Ask for confirmation on stdin.

    Returns ``True`` immediately when ``assume_yes`` is set. A non-interactive
    stdin (``EOFError``) is treated as "no" so the tools never modify files
    without an explicit answer.
    """
    if assume_yes:
        return True

    if not sys.stdin.isatty():
        return False

    try:
        answer = input(f"{question} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        # Treat end-of-input and Ctrl+C as "no" so the tool exits cleanly
        # without modifying any file.
        print()
        return False

    return answer in ("y", "yes")
