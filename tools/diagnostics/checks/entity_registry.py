"""Entity registry checks for BTicino CLASSE100X."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file, storage_file


DEPRECATED_ENTITY_ID_PARTS: tuple[str, ...] = (
    "entrance_hall_bticino_classe100x",
)

BTICINO_PLATFORM_NAMES: tuple[str, ...] = (
    "bticino_classe100x",
    "bticino_classe100x_buttons",
)

BTICINO_REFERENCE = "bticino_classe100x"


class EntityRegistryCheck(HealthCheck):
    """Check Home Assistant entity registry for stale BTicino entries."""

    name = "Entity Registry"
    description = "Checks BTicino entities in the Home Assistant entity registry."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the entity registry check."""
        path = storage_file(config_path, "core.entity_registry")

        if not path.exists():
            return fail_result(
                name=self.name,
                summary="Entity registry file was not found.",
                errors=[f"Missing file: {path}"],
            )

        registry = read_json_file(path)
        entities = registry.get("data", {}).get("entities", [])

        errors: list[str] = []
        details: list[str] = []

        bticino_entities = _find_bticino_entities(entities)

        entity_ids = [
            entity.get("entity_id")
            for entity in bticino_entities
            if entity.get("entity_id")
        ]
        unique_ids = [
            entity.get("unique_id")
            for entity in bticino_entities
            if entity.get("unique_id")
        ]

        duplicated_entity_ids = _find_duplicates(entity_ids)
        duplicated_unique_ids = _find_duplicates(unique_ids)

        deprecated_entities = [
            entity.get("entity_id")
            for entity in bticino_entities
            if any(
                part in str(entity.get("entity_id", ""))
                for part in DEPRECATED_ENTITY_ID_PARTS
            )
        ]

        orphaned_entities = [
            entity.get("entity_id")
            for entity in bticino_entities
            if entity.get("orphaned_timestamp") is not None
        ]

        null_config_entries = [
            entity.get("entity_id")
            for entity in bticino_entities
            if entity.get("config_entry_id") is None
        ]

        if duplicated_entity_ids:
            errors.append("Duplicated entity_id values found:")
            errors.extend(f"  {entity_id}" for entity_id in duplicated_entity_ids)

        if duplicated_unique_ids:
            errors.append("Duplicated unique_id values found:")
            errors.extend(f"  {unique_id}" for unique_id in duplicated_unique_ids)

        if deprecated_entities:
            errors.append("Deprecated BTicino entity IDs found:")
            errors.extend(f"  {entity_id}" for entity_id in deprecated_entities)

        if orphaned_entities:
            errors.append("Orphaned BTicino entities found:")
            errors.extend(f"  {entity_id}" for entity_id in orphaned_entities)

        if null_config_entries:
            errors.append("BTicino entities with null config_entry_id found:")
            errors.extend(f"  {entity_id}" for entity_id in null_config_entries)

        details.extend(
            [
                f"BTicino entities found: {len(bticino_entities)}",
                f"Duplicated entity IDs: {len(duplicated_entity_ids)}",
                f"Duplicated unique IDs: {len(duplicated_unique_ids)}",
                f"Deprecated BTicino entity IDs: {len(deprecated_entities)}",
                f"Orphaned BTicino entities: {len(orphaned_entities)}",
                f"BTicino entities with null config_entry_id: {len(null_config_entries)}",
            ]
        )

        if errors:
            return fail_result(
                name=self.name,
                summary="Entity registry contains BTicino-related problems.",
                errors=errors,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Entity registry looks healthy.",
            details=details,
        )


def _find_duplicates(values: list[str]) -> list[str]:
    """Return duplicated values."""
    return [
        value
        for value, count in Counter(values).items()
        if count > 1
    ]


def _find_bticino_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return BTicino-related entity registry entries."""
    return [
        entity
        for entity in entities
        if entity.get("platform") in BTICINO_PLATFORM_NAMES
        or BTICINO_REFERENCE in str(entity.get("entity_id", ""))
        or BTICINO_REFERENCE in str(entity.get("unique_id", ""))
    ]