#!/usr/bin/env python3
"""Self-test for the BTicino diagnostics entity checks.

Builds synthetic ``.storage`` fixtures from the expected-entity spec and asserts
that the entity-registry and metadata-consistency checks reach the right
verdict: a clean registry passes, and each class of problem (obsolete migrated
entity, incomplete migration, legacy naming, stale ``deleted_entities``, missing
entity, wrong-domain entity, stale config entry, missing unique id, and a
metadata mismatch) is detected.

This locks in the detection logic so it cannot silently regress. It does not
import Home Assistant, so it runs anywhere:

    python3 scripts/validate_health_check.py

Exit code ``0`` means every scenario reached its expected verdict.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from diagnostics.checks.entity_registry import EntityRegistryCheck
from diagnostics.checks.expected_entities import EXPECTED_ENTITIES
from diagnostics.checks.metadata_consistency import MetadataConsistencyCheck
from diagnostics.shared.entities import DOMAIN

HOST = "192.168.50.251"
ENTRY_ID = "abc"
CONFIG_ENTRIES = {
    "data": {
        "entries": [
            {"entry_id": ENTRY_ID, "domain": DOMAIN, "data": {"host": HOST}}
        ]
    }
}


def _unique_id(suffix: str) -> str:
    return f"{DOMAIN}_{HOST}_{suffix}"


def _capabilities(entity: Any) -> dict[str, Any] | None:
    if entity.options is not None:
        return {"options": list(entity.options)}
    if entity.state_class is not None:
        return {"state_class": entity.state_class}
    return None


def clean_registry() -> dict[str, Any]:
    """Build a registry that exactly matches the expected entity spec."""
    entities = [
        {
            "entity_id": expected.default_entity_id,
            "unique_id": expected.unique_id(HOST),
            "platform": DOMAIN,
            "config_entry_id": ENTRY_ID,
            "translation_key": expected.translation_key,
            "entity_category": expected.entity_category,
            "original_device_class": expected.original_device_class,
            "original_icon": expected.original_icon,
            "unit_of_measurement": expected.unit_of_measurement,
            "capabilities": _capabilities(expected),
            "orphaned_timestamp": None,
        }
        for expected in EXPECTED_ENTITIES
    ]
    return {"data": {"entities": entities, "deleted_entities": []}}


def _run(
    mutate: Callable[[dict[str, Any]], None] | None,
    config_entries: dict[str, Any] | None = None,
) -> tuple[str, str, list[str]]:
    registry = clean_registry()
    if mutate is not None:
        mutate(registry)

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        storage = base / ".storage"
        storage.mkdir(parents=True, exist_ok=True)
        (storage / "core.entity_registry").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        (storage / "core.config_entries").write_text(
            json.dumps(config_entries or CONFIG_ENTRIES), encoding="utf-8"
        )

        entity_result = EntityRegistryCheck().run(base)
        metadata_result = MetadataConsistencyCheck().run(base)

    findings = (
        list(entity_result.errors)
        + list(entity_result.warnings)
        + list(metadata_result.warnings)
    )
    return str(entity_result.status), str(metadata_result.status), findings


# --- scenario mutations ---------------------------------------------------


def _obsolete_migrated(registry: dict[str, Any]) -> None:
    for entity in registry["data"]["entities"]:
        if entity["unique_id"] == _unique_id("connection"):
            entity["unique_id"] = _unique_id("connection_status")
            entity["entity_id"] = f"binary_sensor.{DOMAIN}_connection_status"


def _incomplete_migration(registry: dict[str, Any]) -> None:
    registry["data"]["entities"].append(
        {
            "entity_id": "binary_sensor.old_conn",
            "unique_id": _unique_id("connection_status"),
            "platform": DOMAIN,
            "config_entry_id": ENTRY_ID,
            "orphaned_timestamp": None,
        }
    )


def _legacy_naming(registry: dict[str, Any]) -> None:
    registry["data"]["entities"].append(
        {
            "entity_id": f"button.entrance_hall_{DOMAIN}_condominium_gate",
            "unique_id": _unique_id("legacy_gate"),
            "platform": DOMAIN,
            "config_entry_id": ENTRY_ID,
            "orphaned_timestamp": None,
        }
    )


def _stale_deleted(registry: dict[str, Any]) -> None:
    registry["data"]["deleted_entities"].append(
        {
            "entity_id": f"sensor.{DOMAIN}_old",
            "unique_id": _unique_id("old_metric"),
            "platform": DOMAIN,
        }
    )


def _missing_entity(registry: dict[str, Any]) -> None:
    registry["data"]["entities"] = [
        entity
        for entity in registry["data"]["entities"]
        if not entity["unique_id"].endswith("_uptime")
    ]


def _wrong_domain(registry: dict[str, Any]) -> None:
    for entity in registry["data"]["entities"]:
        if entity["unique_id"] == _unique_id("connection"):
            # Correct unique id, wrong domain (sensor instead of binary_sensor).
            entity["entity_id"] = f"sensor.{DOMAIN}_connection_status"


def _stale_config_entry(registry: dict[str, Any]) -> None:
    registry["data"]["entities"][0]["config_entry_id"] = "obsolete-entry"


def _missing_unique_id(registry: dict[str, Any]) -> None:
    registry["data"]["entities"].append(
        {
            "entity_id": f"sensor.{DOMAIN}_ghost",
            "unique_id": None,
            "platform": DOMAIN,
            "config_entry_id": ENTRY_ID,
            "orphaned_timestamp": None,
        }
    )


def _valid_rename_with_room(registry: dict[str, Any]) -> None:
    # A user rename that merely contains a legacy fragment mid-string (not at the
    # start of the object id) must not be flagged as legacy. The unique id is
    # unchanged, so the entity is still matched as present.
    for entity in registry["data"]["entities"]:
        if entity["unique_id"] == _unique_id("condominium_gate"):
            entity["entity_id"] = f"button.my_entrance_hall_{DOMAIN}_condominium_gate"


def _foreign_platform(registry: dict[str, Any]) -> None:
    # An entity that reuses the BTicino unique-id prefix but was created by a
    # different integration (platform) must be flagged, not accepted.
    registry["data"]["entities"].append(
        {
            "entity_id": f"sensor.{DOMAIN}_foreign",
            "unique_id": _unique_id("foreign_metric"),
            "platform": "mqtt",
            "config_entry_id": ENTRY_ID,
            "orphaned_timestamp": None,
        }
    )


def _hacs_entity_ignored(registry: dict[str, Any]) -> None:
    # HACS management entities embed the integration name but belong to HACS.
    # They must be ignored, not flagged as unexpected BTicino entities.
    registry["data"]["entities"].append(
        {
            "entity_id": f"update.{DOMAIN}_update",
            "unique_id": f"{DOMAIN}_update",
            "platform": "hacs",
            "config_entry_id": "hacs-entry",
            "orphaned_timestamp": None,
        }
    )


def _foreign_platform_expected_key(registry: dict[str, Any]) -> None:
    # A foreign-platform entity reusing a *real* expected unique key. The entity
    # registry check must flag it (and report the real one missing), and the
    # metadata check must not compare it — even though its metadata is wrong, it
    # is excluded, so no metadata warning is produced.
    for entity in registry["data"]["entities"]:
        if entity["unique_id"] == _unique_id("health_status"):
            entity["platform"] = "mqtt"
            entity["entity_category"] = "diagnostic"


def _metadata_mismatch(registry: dict[str, Any]) -> None:
    for entity in registry["data"]["entities"]:
        if entity["unique_id"].endswith("_health_status"):
            entity["entity_category"] = "diagnostic"


# --- scenarios ------------------------------------------------------------

MULTIPLE_CONFIG_ENTRIES = {
    "data": {
        "entries": [
            {"entry_id": ENTRY_ID, "domain": DOMAIN, "data": {"host": HOST}},
            {"entry_id": "second", "domain": DOMAIN, "data": {"host": "10.0.0.9"}},
        ]
    }
}

_Mutation = Callable[[dict[str, Any]], None]

SCENARIOS: tuple[
    tuple[str, _Mutation | None, str, str, str | None, dict[str, Any] | None], ...
] = (
    # label, mutation, entity status, metadata status, substring, config override
    ("clean registry", None, "PASS", "PASS", None, None),
    (
        "obsolete migrated entity",
        _obsolete_migrated,
        "FAIL",
        "PASS",
        "deprecated unique_id",
        None,
    ),
    (
        "incomplete migration",
        _incomplete_migration,
        "FAIL",
        "PASS",
        "Migration incomplete",
        None,
    ),
    ("legacy naming", _legacy_naming, "FAIL", "PASS", "Legacy entity_id naming", None),
    (
        "valid rename mentioning a room",
        _valid_rename_with_room,
        "PASS",
        "PASS",
        None,
        None,
    ),
    (
        "stale deleted_entities",
        _stale_deleted,
        "FAIL",
        "PASS",
        "deleted_entities",
        None,
    ),
    (
        "missing expected entity",
        _missing_entity,
        "FAIL",
        "PASS",
        "Missing expected",
        None,
    ),
    ("wrong domain", _wrong_domain, "FAIL", "PASS", "wrong domain", None),
    (
        "stale config entry",
        _stale_config_entry,
        "FAIL",
        "PASS",
        "non-current config_entry_id",
        None,
    ),
    (
        "missing unique_id",
        _missing_unique_id,
        "FAIL",
        "PASS",
        "missing a unique_id",
        None,
    ),
    (
        "foreign platform",
        _foreign_platform,
        "FAIL",
        "PASS",
        "non-BTicino platform",
        None,
    ),
    (
        "foreign platform reusing expected key",
        _foreign_platform_expected_key,
        "FAIL",
        "PASS",
        "non-BTicino platform",
        None,
    ),
    (
        "hacs entity ignored",
        _hacs_entity_ignored,
        "PASS",
        "PASS",
        None,
        None,
    ),
    (
        "metadata mismatch",
        _metadata_mismatch,
        "PASS",
        "WARNING",
        "entity_category",
        None,
    ),
    (
        "multiple config entries",
        None,
        "WARNING",
        "WARNING",
        "exactly one BTicino config entry",
        MULTIPLE_CONFIG_ENTRIES,
    ),
)


def main() -> int:
    """Run every scenario and report the outcome."""
    ok = True
    for label, mutate, want_entity, want_metadata, substring, config in SCENARIOS:
        entity_status, metadata_status, findings = _run(mutate, config)

        problems = []
        if entity_status != want_entity:
            problems.append(f"entity {entity_status}!={want_entity}")
        if metadata_status != want_metadata:
            problems.append(f"metadata {metadata_status}!={want_metadata}")
        if substring is not None and not any(substring in line for line in findings):
            problems.append(f"missing expected finding {substring!r}")

        if problems:
            ok = False
            print(f"FAIL: {label}: {'; '.join(problems)}")
        else:
            print(f"OK: {label} (entity={entity_status}, metadata={metadata_status})")

    if ok:
        print(f"\nAll {len(SCENARIOS)} diagnostics scenarios passed.")
        return 0

    print("\nDiagnostics self-test failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
