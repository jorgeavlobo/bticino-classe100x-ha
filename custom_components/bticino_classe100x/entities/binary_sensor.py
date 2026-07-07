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
from .base import BticinoClasse100xEntity, get_host_from_entry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BTicino CLASSE100X binary sensors."""
    coordinator: BticinoClasse100xCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = get_host_from_entry(entry)

    async_add_entities(
        [
            BticinoClasse100xConnectionSensor(
                coordinator=coordinator,
                host=host,
            )
        ]
    )


class BticinoClasse100xConnectionSensor(
    BticinoClasse100xEntity,
    BinarySensorEntity,
):
    """Connection status sensor for the BTicino CLASSE100X."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        host: str,
    ) -> None:
        """Initialize the connection sensor."""
        super().__init__(
            coordinator=coordinator,
            host=host,
            key="connection_status",
            icon="mdi:connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            unique_key="connection",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the CLASSE100X is reachable."""
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return diagnostic and device information attributes."""
        device_information = self.coordinator.device_information

        return {
            "last_test_result": self.coordinator.last_test_result,
            "last_test_time": self.coordinator.last_test_time,
            "last_successful_test_time": self.coordinator.last_successful_test_time,
            "last_failed_test_time": self.coordinator.last_failed_test_time,
            "last_error": self.coordinator.last_error,
            "hostname": device_information.hostname,
            "kernel": device_information.kernel,
            "uptime": device_information.uptime,
            "mac_address": device_information.mac_address,
            "ssh_latency_ms": device_information.ssh_latency_ms,
            "openwebnet_latency_ms": device_information.openwebnet_latency_ms,
            "firmware_version": device_information.firmware_version,
            "os_release": device_information.os_release,
        }