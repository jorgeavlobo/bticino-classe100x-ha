"""Run all BTicino CLASSE100X cleanup tools."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clean_config_entries import clean_config_entries
from clean_entity_registry import clean_entity_registry
from clean_restore_state import clean_restore_state
from shared.cli import build_parser, get_logger, parse_options


def main() -> None:
    """Run all cleanup tools with the same options."""
    parser = build_parser("Run every BTicino CLASSE100X cleanup tool")
    options = parse_options(parser)
    log = get_logger()

    results = []

    log.info("Cleaning BTicino CLASSE100X config entries...")
    results.append(clean_config_entries(options))

    log.info("Cleaning BTicino CLASSE100X entity registry...")
    results.append(clean_entity_registry(options))

    log.info("Cleaning BTicino CLASSE100X restore state...")
    results.append(clean_restore_state(options))

    if all(results):
        log.info("Cleanup completed.")
    else:
        log.error("Cleanup finished with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
