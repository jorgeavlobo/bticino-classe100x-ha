"""Metadata consistency check for BTicino CLASSE100X.

Home Assistant persists entity metadata in ``core.entity_registry``. After
repeated local development updates, HACS redownloads, migrations or refactors,
that persisted metadata can drift from the current entity definitions even
though the integration code is correct.

This check compares, for every expected entity that is present, the metadata
Home Assistant stored against the values the current integration would produce
(declared in :mod:`diagnostics.checks.expected_entities`). Mismatches are
reported as warnings because they usually mean the registry is stale (a restart
or reload is needed), not that the integration is broken.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diagnostics.checks.expected_entities import EXPECTED_ENTITIES, ExpectedEntity
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

_SUGGESTED_ACTION = (
    "Reload the integration, restart Home Assistant, or clean the stale "
    "registry metadata."
)


class MetadataConsistencyCheck(HealthCheck):
    """Compare persisted entity metadata against the current definitions."""

    name = "Metadata Consistency"
    description = (
        "Compares persisted entity metadata with the current BTicino definitions."
    )

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the metadata consistency check."""
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

        config_entry_ids = set(bticino_config_entry_ids(config_entries))
        host = bticino_host(config_entries)

        # The comparison builds the expected unique ids for a single host, so it
        # only runs when there is exactly one BTicino config entry with a known
        # host; several entries (one per host) would need per-host comparison.
        if len(config_entry_ids) != 1 or host is None:
            return warning_result(
                name=self.name,
                summary="Skipped: needs exactly one BTicino config entry with a known host.",
                warnings=["Metadata consistency could not be verified."],
                details=[
                    f"BTicino config entries found: {len(config_entry_ids)}",
                ],
            )

        entities = registry.get("data", {}).get("entities", [])
        by_unique_id = {
            entity.get("unique_id"): entity
            for entity in find_bticino_entities(entities, config_entry_ids)
            if entity.get("unique_id")
        }

        warnings: list[str] = []
        checked = 0

        for expected in EXPECTED_ENTITIES:
            entity = by_unique_id.get(expected.unique_id(host))
            if entity is None:
                # Presence is reported by the entity registry check; here we only
                # compare metadata for entities that exist.
                continue

            checked += 1
            warnings.extend(_compare_metadata(entity, expected))

        details = [
            f"Expected entities: {len(EXPECTED_ENTITIES)}",
            f"Present entities compared: {checked}",
        ]

        if warnings:
            return warning_result(
                name=self.name,
                summary="Persisted metadata does not match the current definitions.",
                warnings=warnings,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Persisted metadata matches the current definitions.",
            details=details,
        )


def _compare_metadata(
    entity: dict[str, Any], expected: ExpectedEntity
) -> list[str]:
    """Return warnings for each metadata field that does not match."""
    capabilities = entity.get("capabilities") or {}
    actual_options = capabilities.get("options")
    actual_state_class = capabilities.get("state_class")

    comparisons: list[tuple[str, Any, Any]] = [
        ("translation_key", expected.translation_key, entity.get("translation_key")),
        ("entity_category", expected.entity_category, entity.get("entity_category")),
        (
            "original_device_class",
            expected.original_device_class,
            entity.get("original_device_class"),
        ),
        ("original_icon", expected.original_icon, entity.get("original_icon")),
        (
            "unit_of_measurement",
            expected.unit_of_measurement,
            entity.get("unit_of_measurement"),
        ),
        ("state_class", expected.state_class, actual_state_class),
        (
            "options",
            list(expected.options) if expected.options is not None else None,
            actual_options,
        ),
    ]

    warnings: list[str] = []
    for field_name, expected_value, actual_value in comparisons:
        if expected_value != actual_value:
            warnings.append(
                _format_mismatch(
                    entity_id=str(entity.get("entity_id")),
                    field=field_name,
                    expected=expected_value,
                    actual=actual_value,
                )
            )

    return warnings


def _format_mismatch(entity_id: str, field: str, expected: Any, actual: Any) -> str:
    """Return a single-line finding for a metadata mismatch."""
    return (
        f"Metadata mismatch: {entity_id} field '{field}' "
        f"expected {expected!r}, got {actual!r} — {_SUGGESTED_ACTION}"
    )
