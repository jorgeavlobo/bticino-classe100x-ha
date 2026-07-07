"""Clean BTicino CLASSE100X entities from Home Assistant entity registry."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.backup import create_backup
from shared.jsonfile import read_json, write_json
from shared.matching import contains_bticino_reference
from shared.paths import entity_registry_path


def clean_entity_registry(config_path: Path) -> None:
    """Remove BTicino-related entries from core.entity_registry."""
    path = entity_registry_path(config_path)

    if not path.exists():
        print(f"Entity registry not found: {path}")
        return

    backup_path = create_backup(path)
    if backup_path:
        print(f"Backup created: {backup_path}")

    registry = read_json(path)

    entities = registry["data"].get("entities", [])
    deleted_entities = registry["data"].get("deleted_entities", [])

    before_entities = len(entities)
    before_deleted_entities = len(deleted_entities)

    registry["data"]["entities"] = [
        entity for entity in entities if not contains_bticino_reference(entity)
    ]

    registry["data"]["deleted_entities"] = [
        entity
        for entity in deleted_entities
        if not contains_bticino_reference(entity)
    ]

    removed_entities = before_entities - len(registry["data"]["entities"])
    removed_deleted_entities = before_deleted_entities - len(
        registry["data"]["deleted_entities"]
    )

    write_json(path, registry)

    print(f"Removed active entities: {removed_entities}")
    print(f"Removed deleted entities: {removed_deleted_entities}")


def main() -> None:
    """Run the entity registry cleanup tool."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config", help="Home Assistant config path")
    args = parser.parse_args()

    clean_entity_registry(Path(args.config))


if __name__ == "__main__":
    main()
