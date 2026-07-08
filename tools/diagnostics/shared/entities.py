"""Shared helpers for locating BTicino entities in the Home Assistant registry."""

from __future__ import annotations

from typing import Any

from shared.hacs import is_hacs_platform

DOMAIN = "bticino_classe100x"
UNIQUE_ID_PREFIX = f"{DOMAIN}_"


def is_hacs_entity(entity: dict[str, Any]) -> bool:
    """Return true for entities created and managed by HACS."""
    return is_hacs_platform(entity)


def mentions_bticino(entity: dict[str, Any]) -> bool:
    """Return true if an entity's ids reference the BTicino integration."""
    return any(
        isinstance(entity.get(key), str) and DOMAIN in entity[key]
        for key in ("entity_id", "unique_id")
    )


def bticino_config_entries(config_entries: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the BTicino config entries.

    Tolerant of a corrupted or schema-drifted storage file: unexpected shapes
    (a non-dict ``data`` section, a non-list ``entries``, or non-dict entries)
    are skipped rather than raising.
    """
    if not isinstance(config_entries, dict):
        return []
    data = config_entries.get("data")
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("domain") == DOMAIN
    ]


def bticino_config_entry_ids(config_entries: dict[str, Any]) -> list[str]:
    """Return the BTicino config entry IDs."""
    return [
        entry["entry_id"]
        for entry in bticino_config_entries(config_entries)
        if entry.get("entry_id")
    ]


def bticino_host(config_entries: dict[str, Any]) -> str | None:
    """Return the host of the first BTicino config entry, if any."""
    for entry in bticino_config_entries(config_entries):
        host = entry.get("data", {}).get("host")
        if host:
            return str(host)
    return None


def is_bticino_entity(entity: dict[str, Any], config_entry_ids: set[str]) -> bool:
    """Return true if a registry entry belongs to BTicino.

    Detection is deliberately broad so stale entities are still caught even when
    they are no longer linked to the current config entry: an entry counts as
    BTicino when its platform is the integration, its unique id carries the
    integration prefix, or it is still attached to a BTicino config entry.

    HACS management entities are excluded even though their ids embed the
    integration name: they are owned by HACS, not by this integration.
    """
    if is_hacs_entity(entity):
        return False

    if entity.get("platform") == DOMAIN:
        return True

    unique_id = entity.get("unique_id")
    if isinstance(unique_id, str) and unique_id.startswith(UNIQUE_ID_PREFIX):
        return True

    return entity.get("config_entry_id") in config_entry_ids


def find_bticino_entities(
    entities: list[dict[str, Any]], config_entry_ids: set[str]
) -> list[dict[str, Any]]:
    """Return the BTicino entities from a list of registry entries."""
    return [
        entity
        for entity in entities
        if is_bticino_entity(entity, config_entry_ids)
    ]
