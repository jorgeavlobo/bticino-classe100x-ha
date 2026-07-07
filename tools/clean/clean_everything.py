"""Run all BTicino CLASSE100X cleanup tools."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from clean_config_entries import clean_config_entries
from clean_entity_registry import clean_entity_registry
from clean_restore_state import clean_restore_state


def main() -> None:
    """Run all cleanup tools."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config", help="Home Assistant config path")
    args = parser.parse_args()

    config_path = Path(args.config)

    print("Cleaning BTicino CLASSE100X config entries...")
    clean_config_entries(config_path)

    print("Cleaning BTicino CLASSE100X entity registry...")
    clean_entity_registry(config_path)

    print("Cleaning BTicino CLASSE100X restore state...")
    clean_restore_state(config_path)

    print("Cleanup completed.")


if __name__ == "__main__":
    main()
