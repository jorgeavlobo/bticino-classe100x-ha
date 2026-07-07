"""Clean BTicino CLASSE100X config entries from Home Assistant."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.backup import create_backup
from shared.jsonfile import read_json, write_json
from shared.matching import contains_bticino_reference
from shared.paths import config_entries_path


def clean_config_entries(config_path: Path) -> None:
    """Remove BTicino and BTicino-related HomeKit config entries."""
    path = config_entries_path(config_path)

    if not path.exists():
        print(f"Config entries file not found: {path}")
        return

    backup_path = create_backup(path)
    if backup_path:
        print(f"Backup created: {backup_path}")

    config_entries = read_json(path)

    entries = config_entries["data"].get("entries", [])
    before_entries = len(entries)

    config_entries["data"]["entries"] = [
        entry
        for entry in entries
        if not (
            entry.get("domain") == "bticino_classe100x"
            or (
                entry.get("domain") == "homekit"
                and contains_bticino_reference(entry)
            )
        )
    ]

    removed_entries = before_entries - len(config_entries["data"]["entries"])

    write_json(path, config_entries)

    print(f"Removed config entries: {removed_entries}")


def main() -> None:
    """Run the config entries cleanup tool."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config", help="Home Assistant config path")
    args = parser.parse_args()

    clean_config_entries(Path(args.config))


if __name__ == "__main__":
    main()
