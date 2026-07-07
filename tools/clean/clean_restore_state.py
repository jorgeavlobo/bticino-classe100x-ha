"""Clean BTicino CLASSE100X restore states from Home Assistant."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.backup import create_backup
from shared.jsonfile import read_json, write_json
from shared.matching import contains_bticino_reference
from shared.paths import restore_state_path


def clean_restore_state(config_path: Path) -> None:
    """Remove BTicino-related entries from core.restore_state."""
    path = restore_state_path(config_path)

    if not path.exists():
        print(f"Restore state not found: {path}")
        return

    backup_path = create_backup(path)
    if backup_path:
        print(f"Backup created: {backup_path}")

    restore_state = read_json(path)

    entries = restore_state.get("data", [])
    before_entries = len(entries)

    restore_state["data"] = [
        entry for entry in entries if not contains_bticino_reference(entry)
    ]

    removed_entries = before_entries - len(restore_state["data"])

    write_json(path, restore_state)

    print(f"Removed restore state entries: {removed_entries}")


def main() -> None:
    """Run the restore state cleanup tool."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config", help="Home Assistant config path")
    args = parser.parse_args()

    clean_restore_state(Path(args.config))


if __name__ == "__main__":
    main()
