"""Entity registry checks for BTicino CLASSE100X."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file, storage_file


BTICINO_DOMAIN = "bticino_classe100x"

DEPRECATED_ENTITY_ID_PARTS: tuple[str, ...] = (
    "entrance_hall_bticino_classe100x",
)


class EntityRegistryCheck(HealthCheck):
    """Check Home Assistant entity registry for stale BTicino entries."""

    name = "Entity Registry"
    description = "Checks BTicino entities in the Home Assistant entity registry."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the entity registry check."""
        entity_registry_path = storage_file(config_path, "core.entity_registry")
        config_entries_path = storage_file(config_path, "core.config_entries")

        if not entity_registry_path.exists():
            return fail_result(
                name=self.name,
                summary="Entity registry file was not found.",
                errors=[f"Missing file: {entity_registry_path}"],
            )

        if not config_entries_path.exists():
            return fail_result(
                name=self.name,
                summary="Config entries file was not found.",
                errors=[f"Missing file: {config_entries_path}"],
            )

        registry = read_json_file(entity_registry_path)
        config_entries = read_json_file(config_entries_path)

        entities = registry.get("data", {}).get("entities", [])
        bticino_config_entry_ids = _find_bticino_config_entry_ids(config_entries)

        errors: list[str] = []
        warnings: list[str] = []
        details: list[str] = []

        if not bticino_config_entry_ids:
            return fail_result(
                name=self.name,
                summary="No BTicino config entry was found.",
                errors=["Expected one BTicino config entry, found 0."],
            )

        if len(bticino_config_entry_ids) > 1:
            warnings.append(
                f"Multiple BTicino config entries found: {len(bticino_config_entry_ids)}"
            )

        bticino_entities = _find_bticino_entities_by_config_entry(
            entities=entities,
            config_entry_ids=bticino_config_entry_ids,
        )

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
            errors.append("Duplicated BTicino entity_id values found:")
            errors.extend(_format_duplicate_details(bticino_entities, "entity_id", duplicated_entity_ids))

        if duplicated_unique_ids:
            errors.append("Duplicated BTicino unique_id values found:")
            errors.extend(_format_duplicate_details(bticino_entities, "unique_id", duplicated_unique_ids))

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
                f"BTicino config entries found: {len(bticino_config_entry_ids)}",
                f"BTicino entities found: {len(bticino_entities)}",
                f"Duplicated BTicino entity IDs: {len(duplicated_entity_ids)}",
                f"Duplicated BTicino unique IDs: {len(duplicated_unique_ids)}",
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
                warnings=warnings,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Entity registry looks healthy.",
            details=details + warnings,
        )


def _find_bticino_config_entry_ids(config_entries: dict[str, Any]) -> list[str]:
    """Return BTicino config entry IDs."""
    entries = config_entries.get("data", {}).get("entries", [])

    return [
        entry["entry_id"]
        for entry in entries
        if entry.get("domain") == BTICINO_DOMAIN and entry.get("entry_id")
    ]


def _find_bticino_entities_by_config_entry(
    entities: list[dict[str, Any]],
    config_entry_ids: list[str],
) -> list[dict[str, Any]]:
    """Return BTicino entities by matching their config entry ID."""
    config_entry_id_set = set(config_entry_ids)

    return [
        entity
        for entity in entities
        if entity.get("config_entry_id") in config_entry_id_set
    ]


def _find_duplicates(values: list[str]) -> list[str]:
    """Return duplicated values."""
    return [
        value
        for value, count in Counter(values).items()
        if count > 1
    ]


def _format_duplicate_details(
    entities: list[dict[str, Any]],
    field_name: str,
    duplicated_values: list[str],
) -> list[str]:
    """Return readable duplicate details."""
    lines: list[str] = []

    for duplicated_value in duplicated_values:
        lines.append(f"  {field_name}: {duplicated_value}")

        matching_entities = [
            entity
            for entity in entities
            if entity.get(field_name) == duplicated_value
        ]

        for entity in matching_entities:
            lines.append(f"    - {entity.get('entity_id')}")

    return lines