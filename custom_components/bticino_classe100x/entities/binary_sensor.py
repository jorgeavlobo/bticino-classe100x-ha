"""Binary sensor entities for BTicino CLASSE100X."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import BticinoClasse100xCoordinator
from ..device import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BTicino CLASSE100X binary sensors."""
    coordinator: BticinoClasse100xCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BticinoClasse100xConnectionSensor(
                coordinator=coordinator,
                host=entry.data[CONF_HOST],
            )
        ]
    )


class BticinoClasse100xConnectionSensor(
    CoordinatorEntity[BticinoClasse100xCoordinator],
    BinarySensorEntity,
):
    """Connection status sensor for the BTicino CLASSE100X."""

    _attr_name = "Connection Status"
    _attr_icon = "mdi:connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        host: str,
    ) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator)
        self._host = host
        self._attr_unique_id = f"{DOMAIN}_{host}_connection"

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

    @property
    def device_info(self):
        """Return device information."""
        return build_device_info(self.coordinator, self._host)
