"""Matching helpers for BTicino cleanup and migration tools."""

from __future__ import annotations

import json
from typing import Any

from shared.hacs import HACS_ENTITY_ID_PREFIXES, HACS_PLATFORM


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

# The object-id prefix of a current BTicino entity (``<domain>.<prefix><key>``).
BTICINO_OBJECT_ID_PREFIX = "bticino_classe100x_"

# Room prefixes used by an earlier naming strategy that produced object ids like
# ``<room>_bticino_classe100x_<key>`` before the entities adopted
# has_entity_name with a stable ``bticino_classe100x_<key>`` object id.
LEGACY_ROOM_PREFIXES: tuple[str, ...] = (
    "entrance_hall",
    "living_room",
    "kitchen",
    "bedroom",
    "hallway",
)

# Object-id prefixes that mark a legacy room-prefixed BTicino entity. The
# integration name is included so a user-renamed entity that merely mentions a
# room (for example ``living_room_gate``) is not treated as a BTicino id. This
# is the single source of truth for the legacy room-prefix forms, re-exported by
# ``diagnostics/checks/expected_entities.py`` so the cleanup tools, the reference
# scan and the health check never drift.
LEGACY_OBJECT_ID_FRAGMENTS: tuple[str, ...] = tuple(
    f"{room}_{BTICINO_OBJECT_ID_PREFIX}" for room in LEGACY_ROOM_PREFIXES
)


def is_bticino_entity_id(entity_id: Any) -> bool:
    """Return true if an entity_id belongs to BTicino.

    Matches, on the object id (the part after the ``.``), the current object-id
    prefix (``bticino_classe100x_…``), a legacy room-prefixed form
    (``entrance_hall_bticino_classe100x_…`` and the other known rooms), or a
    known exact legacy entity_id. The prefixes are checked with ``startswith``,
    never by bare substring, so an unrelated ``sensor.my_bticino_classe100x_x``
    does not match.
    """
    if not isinstance(entity_id, str):
        return False
    if entity_id in LEGACY_ENTITY_IDS:
        return True
    object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id
    if object_id.startswith(BTICINO_OBJECT_ID_PREFIX):
        return True
    return any(
        object_id.startswith(fragment) for fragment in LEGACY_OBJECT_ID_FRAGMENTS
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

    Restore-state records (a dict carrying a nested ``state`` dict) are matched
    structurally on the entity_id they carry, never on their free-form state
    text: an unrelated entity whose state happens to equal a legacy id (e.g. a
    text/history sensor mirroring another entity) must not be removed.
    """
    if is_hacs_managed(value):
        return False

    if isinstance(value, dict) and isinstance(value.get("state"), dict):
        return is_bticino_entity_id(value["state"].get("entity_id"))

    text = json.dumps(value, ensure_ascii=False)

    return any(item in text for item in BTICINO_STRINGS + LEGACY_ENTITY_IDS)
