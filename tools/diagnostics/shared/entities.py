"""Shared helpers for locating BTicino entities in the Home Assistant registry."""

from __future__ import annotations

from typing import Any

DOMAIN = "bticino_classe100x"
UNIQUE_ID_PREFIX = f"{DOMAIN}_"


def bticino_config_entries(config_entries: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the BTicino config entries."""
    entries = config_entries.get("data", {}).get("entries", [])
    return [entry for entry in entries if entry.get("domain") == DOMAIN]


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
    """
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
    return [entity for entity in entities if is_bticino_entity(entity, config_entry_ids)]
