"""Entity registry checks for BTicino CLASSE100X."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from diagnostics.checks.expected_entities import (
    DOMAIN,
    EXPECTED_ENTITIES,
    LEGACY_ENTITY_ID_FRAGMENTS,
)
from diagnostics.shared.check import HealthCheck
from diagnostics.shared.entities import (
    bticino_config_entry_ids,
    bticino_host,
    find_bticino_entities,
)
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file, storage_file


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

        data = registry.get("data", {})
        entities = data.get("entities", [])
        deleted_entities = data.get("deleted_entities", [])

        config_entry_ids = set(bticino_config_entry_ids(config_entries))
        host = bticino_host(config_entries)

        errors: list[str] = []
        warnings: list[str] = []
        details: list[str] = []

        if not config_entry_ids:
            warnings.append("No BTicino config entry was found.")
        elif len(config_entry_ids) > 1:
            warnings.append(
                f"Multiple BTicino config entries found: {len(config_entry_ids)}"
            )

        bticino_entities = find_bticino_entities(entities, config_entry_ids)
        bticino_deleted = find_bticino_entities(deleted_entities, config_entry_ids)

        # Structural integrity of the active entities.
        errors.extend(_check_duplicates(bticino_entities))
        errors.extend(_check_orphans_and_null_config(bticino_entities))
        errors.extend(_check_legacy_naming(bticino_entities))

        # Deleted BTicino entities are historical migration artefacts and should
        # not remain in the registry.
        errors.extend(_check_deleted_entities(bticino_deleted))

        # Expected-versus-actual comparison needs the host to build the exact
        # unique ids the integration would create.
        if host is None:
            warnings.append(
                "Could not determine the BTicino host; skipping "
                "expected-versus-actual entity comparison."
            )
        else:
            errors.extend(_check_expected_versus_actual(bticino_entities, host))

        details.extend(
            [
                f"BTicino config entries found: {len(config_entry_ids)}",
                f"BTicino entities found: {len(bticino_entities)}",
                f"BTicino deleted entities found: {len(bticino_deleted)}",
                f"Expected entities: {len(EXPECTED_ENTITIES)}",
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


def _check_duplicates(entities: list[dict[str, Any]]) -> list[str]:
    """Return errors for duplicated entity_id or unique_id values."""
    errors: list[str] = []

    entity_ids = [e.get("entity_id") for e in entities if e.get("entity_id")]
    unique_ids = [e.get("unique_id") for e in entities if e.get("unique_id")]

    duplicated_entity_ids = _find_duplicates(entity_ids)
    duplicated_unique_ids = _find_duplicates(unique_ids)

    if duplicated_entity_ids:
        errors.append("Duplicated BTicino entity_id values found:")
        errors.extend(_format_duplicates(entities, "entity_id", duplicated_entity_ids))

    if duplicated_unique_ids:
        errors.append("Duplicated BTicino unique_id values found:")
        errors.extend(_format_duplicates(entities, "unique_id", duplicated_unique_ids))

    return errors


def _check_orphans_and_null_config(entities: list[dict[str, Any]]) -> list[str]:
    """Return errors for orphaned entities and entities with no config entry."""
    errors: list[str] = []

    orphaned = [
        e.get("entity_id")
        for e in entities
        if e.get("orphaned_timestamp") is not None
    ]
    null_config = [
        e.get("entity_id")
        for e in entities
        if e.get("config_entry_id") is None
    ]

    if orphaned:
        errors.append("Orphaned BTicino entities found:")
        errors.extend(f"  {entity_id}" for entity_id in orphaned)

    if null_config:
        errors.append("BTicino entities with null config_entry_id found:")
        errors.extend(f"  {entity_id}" for entity_id in null_config)

    return errors


def _check_legacy_naming(entities: list[dict[str, Any]]) -> list[str]:
    """Return errors for entities using legacy entity_id naming."""
    errors: list[str] = []

    for entity in entities:
        entity_id = str(entity.get("entity_id", ""))
        if any(fragment in entity_id for fragment in LEGACY_ENTITY_ID_FRAGMENTS):
            errors.extend(
                _format_obsolete(
                    entity,
                    reason="Legacy entity_id naming from a previous version.",
                    action="Remove obsolete entity from the entity registry.",
                )
            )

    return errors


def _check_deleted_entities(deleted: list[dict[str, Any]]) -> list[str]:
    """Return errors for BTicino entities lingering in deleted_entities."""
    errors: list[str] = []

    if deleted:
        errors.append(
            f"BTicino entities remain in deleted_entities: {len(deleted)}"
        )
        for entity in deleted:
            errors.extend(
                _format_obsolete(
                    entity,
                    reason="Stale entry in deleted_entities from a past migration.",
                    action="Remove the stale entry from deleted_entities.",
                )
            )

    return errors


def _check_expected_versus_actual(
    entities: list[dict[str, Any]], host: str
) -> list[str]:
    """Compare the active BTicino entities against the expected set."""
    errors: list[str] = []

    expected_by_unique_id = {
        entity.unique_id(host): entity for entity in EXPECTED_ENTITIES
    }
    deprecated_by_unique_id: dict[str, Any] = {}
    for entity in EXPECTED_ENTITIES:
        for old_key in entity.deprecated_unique_keys:
            deprecated_by_unique_id[f"{DOMAIN}_{host}_{old_key}"] = entity

    present_unique_ids = {
        e.get("unique_id") for e in entities if e.get("unique_id")
    }

    # Missing expected entities.
    for unique_id, expected in expected_by_unique_id.items():
        if unique_id not in present_unique_ids:
            errors.append(
                f"Missing expected BTicino entity: {expected.default_entity_id} "
                f"(unique_id: {unique_id})"
            )

    # Incomplete migrations: a new unique id and one of its deprecated
    # predecessors both present.
    for old_unique_id, expected in deprecated_by_unique_id.items():
        new_unique_id = expected.unique_id(host)
        if old_unique_id in present_unique_ids and new_unique_id in present_unique_ids:
            errors.append("Migration incomplete.")
            errors.append(f"  Expected unique_id: {new_unique_id}")
            errors.append(f"  Obsolete unique_id still present: {old_unique_id}")
            errors.append(
                "  Suggested action: remove the obsolete migrated entity."
            )

    # Obsolete and unexpected active entities.
    for entity in entities:
        # Legacy-named entities are already reported by the legacy-naming check.
        entity_id = str(entity.get("entity_id", ""))
        if any(fragment in entity_id for fragment in LEGACY_ENTITY_ID_FRAGMENTS):
            continue

        unique_id = entity.get("unique_id")
        if unique_id in expected_by_unique_id or unique_id is None:
            expected = expected_by_unique_id.get(unique_id)
            if expected is not None and entity.get("platform") not in (DOMAIN, None):
                errors.append(
                    f"BTicino entity on unexpected platform: "
                    f"{entity.get('entity_id')} (platform: {entity.get('platform')})"
                )
            continue

        if unique_id in deprecated_by_unique_id:
            errors.extend(
                _format_obsolete(
                    entity,
                    reason="Obsolete migrated entity (deprecated unique_id).",
                    action="Remove obsolete entity from the entity registry.",
                )
            )
        else:
            errors.extend(
                _format_obsolete(
                    entity,
                    reason="Unexpected BTicino entity (unrecognised unique_id).",
                    action="Remove the entity if it is a leftover from a past version.",
                )
            )

    return errors


def _format_obsolete(entity: dict[str, Any], reason: str, action: str) -> list[str]:
    """Return readable, cleanup-oriented details for an obsolete entity."""
    return [
        "Obsolete BTicino entity found:",
        f"  Entity ID: {entity.get('entity_id')}",
        f"  Unique ID: {entity.get('unique_id')}",
        f"  Reason: {reason}",
        f"  Suggested action: {action}",
    ]


def _find_duplicates(values: list[str]) -> list[str]:
    """Return duplicated values."""
    return [value for value, count in Counter(values).items() if count > 1]


def _format_duplicates(
    entities: list[dict[str, Any]],
    field_name: str,
    duplicated_values: list[str],
) -> list[str]:
    """Return readable duplicate details."""
    lines: list[str] = []

    for duplicated_value in duplicated_values:
        lines.append(f"  {field_name}: {duplicated_value}")
        for entity in entities:
            if entity.get(field_name) == duplicated_value:
                lines.append(f"    - {entity.get('entity_id')}")

    return lines
