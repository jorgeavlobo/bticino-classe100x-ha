"""Matching helpers for BTicino cleanup and migration tools."""

from __future__ import annotations

import json
from typing import Any


BTICINO_STRINGS: tuple[str, ...] = (
    "bticino_classe100x",
    "bticino_classe100x_buttons",
    "entrance_hall_bticino_classe100x",
)

LEGACY_ENTITY_IDS: tuple[str, ...] = (
    "button.condominium_gate",
    "button.pedestrian_door",
    "input_boolean.condominium_gate",
    "input_boolean.pedestrian_door",
    "automation.condominium_gate_opening",
    "automation.pedestrian_door_opening",
)

# HACS creates its own management entities for the integration (an ``update``
# entity and a ``pre_release`` switch). Their ids embed the integration name but
# they belong to HACS and must never be treated as BTicino entries for cleanup.
HACS_PLATFORM = "hacs"
HACS_ENTITY_ID_PREFIXES: tuple[str, ...] = (
    "update.bticino_classe100x",
    "switch.bticino_classe100x",
)


def _entity_id_of(value: Any) -> str | None:
    """Return the entity_id carried by a registry or restore-state entry."""
    if not isinstance(value, dict):
        return None

    entity_id = value.get("entity_id")
    if isinstance(entity_id, str):
        return entity_id

    state = value.get("state")
    if isinstance(state, dict):
        entity_id = state.get("entity_id")
        if isinstance(entity_id, str):
            return entity_id

    return None


def is_hacs_managed(value: Any) -> bool:
    """Return true when a value describes a HACS-managed entity.

    When the value carries a ``platform`` (entity registry entries) it is
    trusted exclusively, so an integration-provided ``update``/``switch`` entity
    is never misclassified. The entity_id-prefix heuristic is only used as a
    fallback for restore-state entries, which do not carry the platform.
    """
    if isinstance(value, dict) and "platform" in value:
        return value.get("platform") == HACS_PLATFORM

    entity_id = _entity_id_of(value)
    return entity_id is not None and entity_id.startswith(HACS_ENTITY_ID_PREFIXES)


def contains_bticino_reference(value: Any) -> bool:
    """Return true if an object contains BTicino-related data.

    HACS-managed entities are never matched even though their ids embed the
    integration name, so the cleanup tools never remove them.
    """
    if is_hacs_managed(value):
        return False

    text = json.dumps(value, ensure_ascii=False)

    return any(item in text for item in BTICINO_STRINGS + LEGACY_ENTITY_IDS)
