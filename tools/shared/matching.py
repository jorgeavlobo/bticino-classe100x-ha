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


def contains_bticino_reference(value: Any) -> bool:
    """Return true if an object contains BTicino-related data."""
    text = json.dumps(value, ensure_ascii=False)

    return any(item in text for item in BTICINO_STRINGS + LEGACY_ENTITY_IDS)
