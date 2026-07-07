"""Shared entity descriptions for BTicino CLASSE100X entities.

Centralizing the description classes here keeps them out of the individual
platform files and lets future platforms reuse the same, consistent shapes.
Each description extends the native Home Assistant ``EntityDescription`` for its
platform, which acts as the common base.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import EntityCategory

from ..coordinator import BticinoClasse100xCoordinator


@dataclass(frozen=True, kw_only=True)
class BticinoButtonDescription(ButtonEntityDescription):
    """Description of a BTicino CLASSE100X button entity."""

    button_type: str
    press_command: str | None = None
    release_command: str | None = None


@dataclass(frozen=True, kw_only=True)
class BticinoBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a BTicino CLASSE100X binary sensor entity."""

    value_fn: Callable[[BticinoClasse100xCoordinator], bool]
    unique_key: str | None = None
    attributes_fn: (
        Callable[[BticinoClasse100xCoordinator], dict[str, str | int | None]] | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class BticinoSensorDescription(SensorEntityDescription):
    """Description of a BTicino CLASSE100X sensor entity."""

    value_fn: Callable[[BticinoClasse100xCoordinator], Any]
    entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC
