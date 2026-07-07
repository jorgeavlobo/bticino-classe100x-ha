"""Binary sensor entities for BTicino CLASSE100X."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import BticinoClasse100xCoordinator
from .base import BticinoClasse100xEntity
from .descriptions import BticinoBinarySensorDescription


def _connection_attributes(
    coordinator: BticinoClasse100xCoordinator,
) -> dict[str, str | int | None]:
    """Return diagnostic and device information attributes."""
    device_information = coordinator.device_information

    return {
        "last_test_result": coordinator.last_test_result,
        "last_test_time": coordinator.last_test_time,
        "last_successful_test_time": coordinator.last_successful_test_time,
        "last_failed_test_time": coordinator.last_failed_test_time,
        "last_error": coordinator.last_error,
        "hostname": device_information.hostname,
        "kernel": device_information.kernel,
        "uptime": device_information.uptime,
        "mac_address": device_information.mac_address,
        "ssh_latency_ms": device_information.ssh_latency_ms,
        "openwebnet_latency_ms": device_information.openwebnet_latency_ms,
        "firmware_version": device_information.firmware_version,
        "os_release": device_information.os_release,
    }


BINARY_SENSOR_DESCRIPTIONS: tuple[BticinoBinarySensorDescription, ...] = (
    BticinoBinarySensorDescription(
        key="connection_status",
        unique_key="connection",
        icon="mdi:connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: bool(coordinator.data),
        attributes_fn=_connection_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BTicino CLASSE100X binary sensors."""
    coordinator: BticinoClasse100xCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        BticinoClasse100xBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class BticinoClasse100xBinarySensor(
    BticinoClasse100xEntity,
    BinarySensorEntity,
):
    """Representation of a BTicino CLASSE100X binary sensor."""

    entity_description: BticinoBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return true when the CLASSE100X is reachable."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None] | None:
        """Return diagnostic and device information attributes."""
        if self.entity_description.attributes_fn is None:
            return None

        return self.entity_description.attributes_fn(self.coordinator)
