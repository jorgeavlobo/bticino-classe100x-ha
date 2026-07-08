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
from diagnostics.shared.result import (
    HealthCheckResult,
    fail_result,
    pass_result,
    warning_result,
)
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
        errors.extend(_check_orphans_and_config(bticino_entities, config_entry_ids))
        errors.extend(_check_legacy_naming(bticino_entities))

        # Deleted BTicino entities are historical migration artefacts and should
        # not remain in the registry.
        errors.extend(_check_deleted_entities(bticino_deleted))

        # The expected-versus-actual comparison builds the exact unique ids the
        # integration would create for a single host, so it only runs when there
        # is exactly one BTicino config entry with a known host. With several
        # entries (one per host) a single-host comparison would misclassify the
        # other hosts' entities, so it is skipped with a warning.
        if len(config_entry_ids) == 1 and host is not None:
            errors.extend(_check_expected_versus_actual(bticino_entities, host))
        else:
            warnings.append(
                "Skipping the expected-versus-actual entity comparison "
                "(needs exactly one BTicino config entry with a known host)."
            )

        details = [
            f"BTicino config entries found: {len(config_entry_ids)}",
            f"BTicino entities found: {len(bticino_entities)}",
            f"BTicino deleted entities found: {len(bticino_deleted)}",
            f"Expected entities: {len(EXPECTED_ENTITIES)}",
        ]

        if errors:
            return fail_result(
                name=self.name,
                summary="Entity registry contains BTicino-related problems.",
                errors=errors,
                warnings=warnings,
                details=details,
            )

        if warnings:
            return warning_result(
                name=self.name,
                summary="Entity registry could not be fully validated.",
                warnings=warnings,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Entity registry looks healthy.",
            details=details,
        )


def _entity_domain(entity: dict[str, Any]) -> str:
    """Return the entity domain (the part of the entity_id before the dot)."""
    entity_id = str(entity.get("entity_id", ""))
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _object_id(entity: dict[str, Any]) -> str:
    """Return the object id (the part of the entity_id after the dot)."""
    entity_id = str(entity.get("entity_id", ""))
    return entity_id.split(".", 1)[1] if "." in entity_id else entity_id


def _is_legacy_entity(entity: dict[str, Any]) -> bool:
    """Return true when the object id starts with a legacy naming fragment.

    Matching only at the start of the object id avoids flagging a user-renamed
    entity that merely contains a legacy fragment somewhere in the middle.
    """
    object_id = _object_id(entity)
    return any(
        object_id.startswith(fragment) for fragment in LEGACY_ENTITY_ID_FRAGMENTS
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


def _check_orphans_and_config(
    entities: list[dict[str, Any]], config_entry_ids: set[str]
) -> list[str]:
    """Return errors for orphaned entities and bad config-entry links."""
    errors: list[str] = []

    for entity in entities:
        entity_id = entity.get("entity_id")

        if entity.get("orphaned_timestamp") is not None:
            errors.append(f"Orphaned BTicino entity: {entity_id}")

        config_entry_id = entity.get("config_entry_id")
        if config_entry_id is None:
            errors.append(f"BTicino entity with null config_entry_id: {entity_id}")
        elif config_entry_id not in config_entry_ids:
            errors.append(
                f"BTicino entity linked to a non-current config_entry_id: "
                f"{entity_id} (config_entry_id: {config_entry_id})"
            )

    return errors


def _check_legacy_naming(entities: list[dict[str, Any]]) -> list[str]:
    """Return errors for entities using legacy entity_id naming."""
    return [
        _format_obsolete(
            entity,
            reason="Legacy entity_id naming from a previous version.",
            action="Remove obsolete entity from the entity registry.",
        )
        for entity in entities
        if _is_legacy_entity(entity)
    ]


def _check_deleted_entities(deleted: list[dict[str, Any]]) -> list[str]:
    """Return errors for BTicino entities lingering in deleted_entities."""
    if not deleted:
        return []

    errors = [f"BTicino entities remain in deleted_entities: {len(deleted)}"]
    errors.extend(
        _format_obsolete(
            entity,
            reason="Stale entry in deleted_entities from a past migration.",
            action="Remove the stale entry from deleted_entities.",
        )
        for entity in deleted
    )
    return errors


def _check_expected_versus_actual(
    entities: list[dict[str, Any]], host: str
) -> list[str]:
    """Compare the active BTicino entities against the expected set.

    Entities are matched on ``(domain, unique_id)`` — the same identity Home
    Assistant enforces — so an entry with the right unique id under the wrong
    domain is treated as a wrong-domain artefact, not a valid entity.
    """
    errors: list[str] = []

    expected_by_key = {
        (entity.platform, entity.unique_id(host)): entity
        for entity in EXPECTED_ENTITIES
    }
    deprecated_by_key: dict[tuple[str, str], Any] = {}
    expected_domains_by_unique_id: dict[str, set[str]] = {}
    for entity in EXPECTED_ENTITIES:
        expected_domains_by_unique_id.setdefault(entity.unique_id(host), set()).add(
            entity.platform
        )
        for old_key in entity.deprecated_unique_keys:
            deprecated_by_key[(entity.platform, f"{DOMAIN}_{host}_{old_key}")] = entity

    present_keys = {
        (_entity_domain(entity), entity["unique_id"])
        for entity in entities
        if entity.get("unique_id")
    }

    # Missing expected entities.
    for (domain, unique_id), expected in expected_by_key.items():
        if (domain, unique_id) not in present_keys:
            errors.append(
                f"Missing expected BTicino entity: {expected.default_entity_id} "
                f"(unique_id: {unique_id})"
            )

    # Incomplete migrations: a new unique id and one of its deprecated
    # predecessors both present in the same domain.
    for (domain, old_unique_id), expected in deprecated_by_key.items():
        new_unique_id = expected.unique_id(host)
        if (domain, old_unique_id) in present_keys and (
            domain,
            new_unique_id,
        ) in present_keys:
            errors.append(
                f"Migration incomplete: expected {new_unique_id}, obsolete "
                f"{old_unique_id} still present — remove the obsolete migrated entity."
            )

    # Obsolete and unexpected active entities.
    for entity in entities:
        # Legacy-named entities are already reported by the legacy-naming check.
        if _is_legacy_entity(entity):
            continue

        unique_id = entity.get("unique_id")
        if unique_id is None:
            errors.append(
                _format_obsolete(
                    entity,
                    reason="BTicino entity is missing a unique_id.",
                    action="Remove the entity if it is a leftover from a past version.",
                )
            )
            continue

        domain = _entity_domain(entity)
        if (domain, unique_id) in expected_by_key:
            continue

        if (domain, unique_id) in deprecated_by_key:
            errors.append(
                _format_obsolete(
                    entity,
                    reason="Obsolete migrated entity (deprecated unique_id).",
                    action="Remove obsolete entity from the entity registry.",
                )
            )
        elif unique_id in expected_domains_by_unique_id and (
            domain not in expected_domains_by_unique_id[unique_id]
        ):
            expected_domains = ", ".join(
                sorted(expected_domains_by_unique_id[unique_id])
            )
            errors.append(
                _format_obsolete(
                    entity,
                    reason=f"Entity is in the wrong domain (expected {expected_domains}).",
                    action="Remove the wrong-domain entity from the entity registry.",
                )
            )
        else:
            errors.append(
                _format_obsolete(
                    entity,
                    reason="Unexpected BTicino entity (unrecognised unique_id).",
                    action="Remove the entity if it is a leftover from a past version.",
                )
            )

    return errors


def _format_obsolete(entity: dict[str, Any], reason: str, action: str) -> str:
    """Return a single-line, cleanup-oriented finding for an obsolete entity."""
    return (
        f"Obsolete BTicino entity: {entity.get('entity_id')} "
        f"(unique_id: {entity.get('unique_id')}) — {reason} "
        f"Suggested action: {action}"
    )


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
