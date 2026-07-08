"""Clean BTicino CLASSE100X entities from Home Assistant entity registry."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.cleaner import run_cleanup
from shared.cli import ToolOptions, build_parser, parse_options
from shared.matching import contains_bticino_reference
from shared.paths import entity_registry_path


def clean_entity_registry(options: ToolOptions) -> bool:
    """Remove BTicino-related entries from core.entity_registry."""

    def mutate(registry: dict) -> dict[str, int]:
        data = registry.get("data", {})
        entities = data.get("entities", [])
        deleted_entities = data.get("deleted_entities", [])

        kept_entities = [
            entity for entity in entities if not contains_bticino_reference(entity)
        ]
        kept_deleted = [
            entity
            for entity in deleted_entities
            if not contains_bticino_reference(entity)
        ]

        data["entities"] = kept_entities
        data["deleted_entities"] = kept_deleted

        return {
            "active entities": len(entities) - len(kept_entities),
            "deleted entities": len(deleted_entities) - len(kept_deleted),
        }

    return run_cleanup(options, entity_registry_path(options.config_path), mutate)


def main() -> None:
    """Run the entity registry cleanup tool."""
    parser = build_parser("Clean BTicino entities from core.entity_registry")
    if not clean_entity_registry(parse_options(parser)):
        sys.exit(1)


if __name__ == "__main__":
    main()
