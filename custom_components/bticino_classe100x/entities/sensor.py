"""Sensor entities for BTicino CLASSE100X."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import BticinoClasse100xCoordinator
from ..device import build_device_info


HEALTH_STATUS_HEALTHY = "Healthy"
HEALTH_STATUS_SLOW = "Slow"
HEALTH_STATUS_OFFLINE = "Offline"

SLOW_LATENCY_THRESHOLD_MS = 2000


@dataclass(frozen=True, kw_only=True)
class BticinoSensorDescription(SensorEntityDescription):
    """Description of a BTicino CLASSE100X sensor."""

    value_fn: Callable[[BticinoClasse100xCoordinator], Any]


def _get_health_status(coordinator: BticinoClasse100xCoordinator) -> str:
    """Return the current health status for the CLASSE100X."""
    if not coordinator.data:
        return HEALTH_STATUS_OFFLINE

    device_information = coordinator.device_information

    ssh_latency_ms = device_information.ssh_latency_ms
    openwebnet_latency_ms = device_information.openwebnet_latency_ms

    if ssh_latency_ms is not None and ssh_latency_ms > SLOW_LATENCY_THRESHOLD_MS:
        return HEALTH_STATUS_SLOW

    if (
        openwebnet_latency_ms is not None
        and openwebnet_latency_ms > SLOW_LATENCY_THRESHOLD_MS
    ):
        return HEALTH_STATUS_SLOW

    return HEALTH_STATUS_HEALTHY


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp string into a timezone-aware datetime."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.astimezone()

    return parsed

def _last_failed_status(
    coordinator: BticinoClasse100xCoordinator,
) -> str:
    """Return a human readable failed-test status."""

    if coordinator.last_failed_test_time is None:
        return "Never"

    return "Failed"

SENSOR_DESCRIPTIONS: tuple[BticinoSensorDescription, ...] = (
    BticinoSensorDescription(
        key="health_status",
        name="Health Status",
        icon="mdi:heart-pulse",
        value_fn=_get_health_status,
    ),
    BticinoSensorDescription(
        key="ssh_latency",
        name="SSH Latency",
        icon="mdi:lan",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda coordinator: coordinator.device_information.ssh_latency_ms,
    ),
    BticinoSensorDescription(
        key="openwebnet_latency",
        name="OpenWebNet Latency",
        icon="mdi:connection",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda coordinator: coordinator.device_information.openwebnet_latency_ms,
    ),
    BticinoSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        value_fn=lambda coordinator: coordinator.device_information.firmware_version,
    ),
    BticinoSensorDescription(
        key="os_release",
        name="OS Release",
        icon="mdi:linux",
        value_fn=lambda coordinator: coordinator.device_information.os_release,
    ),
    BticinoSensorDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        value_fn=lambda coordinator: coordinator.device_information.uptime,
    ),
    BticinoSensorDescription(
        key="hostname",
        name="Hostname",
        icon="mdi:server",
        value_fn=lambda coordinator: coordinator.device_information.hostname,
    ),
    BticinoSensorDescription(
        key="mac_address",
        name="MAC Address",
        icon="mdi:network-outline",
        value_fn=lambda coordinator: coordinator.device_information.mac_address,
    ),
    BticinoSensorDescription(
        key="last_test_result",
        name="Last Test Result",
        icon="mdi:check-network-outline",
        value_fn=lambda coordinator: coordinator.last_test_result,
    ),
    BticinoSensorDescription(
        key="last_successful_test",
        name="Last Successful Test",
        icon="mdi:check-circle-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: _parse_timestamp(
            coordinator.last_successful_test_time
        ),
    ),
    BticinoSensorDescription(
        key="last_failed_test_status",
        name="Last Failed Status",
        icon="mdi:alert-circle-outline",
        value_fn=_last_failed_status,
    ),
    BticinoSensorDescription(
        key="last_failed_test",
        name="Last Failed Test",
        icon="mdi:alert-circle-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: _parse_timestamp(
            coordinator.last_failed_test_time
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BTicino CLASSE100X sensors."""
    coordinator: BticinoClasse100xCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BticinoClasse100xSensor(
                coordinator=coordinator,
                host=entry.data[CONF_HOST],
                description=description,
            )
            for description in SENSOR_DESCRIPTIONS
        ]
    )


class BticinoClasse100xSensor(
    CoordinatorEntity[BticinoClasse100xCoordinator],
    SensorEntity,
):
    """Representation of a BTicino CLASSE100X sensor."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        host: str,
        description: BticinoSensorDescription,
    ) -> None:
        """Initialize the BTicino CLASSE100X sensor."""
        super().__init__(coordinator)

        self._host = host
        self.entity_description = description

        self._attr_name = description.name
        self._attr_unique_id = f"{DOMAIN}_{host}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor native value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def device_info(self):
        """Return device information."""
        return build_device_info(self.coordinator, self._host)
