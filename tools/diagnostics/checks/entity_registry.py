"""Entity registry checks for BTicino CLASSE100X."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from diagnostics.shared.result import HealthCheckResult
from diagnostics.shared.storage import read_json_file, storage_file


DEPRECATED_ENTITY_ID_PARTS: tuple[str, ...] = (
    "entrance_hall_bticino_classe100x",
)

BTICINO_PLATFORM_NAMES: tuple[str, ...] = (
    "bticino_classe100x",
    "bticino_classe100x_buttons",
)

BTICINO_REFERENCE = "bticino_classe100x"


def check_entity_registry(config_path: Path) -> HealthCheckResult:
    """Check Home Assistant entity registry for stale BTicino entries."""
    path = storage_file(config_path, "core.entity_registry")

    if not path.exists():
        return HealthCheckResult(
            name="Entity Registry",
            passed=False,
            errors=[f"Entity registry file not found: {path}"],
        )

    registry = read_json_file(path)
    entities = registry.get("data", {}).get("entities", [])

    errors: list[str] = []
    warnings: list[str] = []
    details: list[str] = []

    entity_ids = [entity.get("entity_id") for entity in entities if entity.get("entity_id")]
    unique_ids = [entity.get("unique_id") for entity in entities if entity.get("unique_id")]

    duplicated_entity_ids = [
        entity_id
        for entity_id, count in Counter(entity_ids).items()
        if count > 1
    ]

    duplicated_unique_ids = [
        unique_id
        for unique_id, count in Counter(unique_ids).items()
        if count > 1
    ]

    if duplicated_entity_ids:
        errors.append("Duplicated entity_id values found:")
        errors.extend(f"  {entity_id}" for entity_id in duplicated_entity_ids)

    if duplicated_unique_ids:
        errors.append("Duplicated unique_id values found:")
        errors.extend(f"  {unique_id}" for unique_id in duplicated_unique_ids)

    bticino_entities = [
        entity
        for entity in entities
        if entity.get("platform") in BTICINO_PLATFORM_NAMES
        or BTICINO_REFERENCE in str(entity.get("entity_id", ""))
        or BTICINO_REFERENCE in str(entity.get("unique_id", ""))
    ]

    deprecated_entities = [
        entity.get("entity_id")
        for entity in bticino_entities
        if any(part in str(entity.get("entity_id", "")) for part in DEPRECATED_ENTITY_ID_PARTS)
    ]

    if deprecated_entities:
        errors.append("Deprecated BTicino entity IDs found:")
        errors.extend(f"  {entity_id}" for entity_id in deprecated_entities)

    orphaned_entities = [
        entity.get("entity_id")
        for entity in bticino_entities
        if entity.get("orphaned_timestamp") is not None
    ]

    if orphaned_entities:
        errors.append("Orphaned BTicino entities found:")
        errors.extend(f"  {entity_id}" for entity_id in orphaned_entities)

    null_config_entries = [
        entity.get("entity_id")
        for entity in bticino_entities
        if entity.get("config_entry_id") is None
    ]

    if null_config_entries:
        errors.append("BTicino entities with null config_entry_id found:")
        errors.extend(f"  {entity_id}" for entity_id in null_config_entries)

    details.append(f"BTicino entities found: {len(bticino_entities)}")

    return HealthCheckResult(
        name="Entity Registry",
        passed=not errors,
        warnings=warnings,
        errors=errors,
        details=details,
    )