"""Run all BTicino CLASSE100X cleanup tools."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from clean_config_entries import clean_config_entries
from clean_entity_registry import clean_entity_registry
from clean_restore_state import clean_restore_state
from shared.cli import build_parser, get_logger, parse_options


def main() -> None:
    """Run all cleanup tools with the same options."""
    parser = build_parser("Run every BTicino CLASSE100X cleanup tool")
    options = parse_options(parser)
    log = get_logger()

    log.info("Cleaning BTicino CLASSE100X config entries...")
    clean_config_entries(options)

    log.info("Cleaning BTicino CLASSE100X entity registry...")
    clean_entity_registry(options)

    log.info("Cleaning BTicino CLASSE100X restore state...")
    clean_restore_state(options)

    log.info("Cleanup completed.")


if __name__ == "__main__":
    main()
