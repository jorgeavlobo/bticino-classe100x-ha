"""Sensor entities for BTicino CLASSE100X."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN, TEST_RESULT_FAILED, TEST_RESULT_SUCCESS
from ..coordinator import BticinoClasse100xCoordinator
from .base import BticinoClasse100xEntity
from .descriptions import BticinoSensorDescription


# Sensor state values are slugs so Home Assistant can translate them through the
# entity ``state`` translation keys. The user-visible labels live in the
# translation files, not in Python.
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_SLOW = "slow"
HEALTH_STATUS_OFFLINE = "offline"

HEALTH_STATUS_OPTIONS = [
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_SLOW,
    HEALTH_STATUS_OFFLINE,
]

LAST_TEST_RESULT_OPTIONS = [TEST_RESULT_SUCCESS, TEST_RESULT_FAILED]

FAILED_STATUS_NEVER = "never"
FAILED_STATUS_FAILED = "failed"
FAILED_STATUS_OPTIONS = [FAILED_STATUS_NEVER, FAILED_STATUS_FAILED]

SLOW_LATENCY_THRESHOLD_MS = 2000


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
    """Return the failed-test status as an enum state slug.

    The returned value ("never"/"failed") is translated to a human-readable
    label through the entity ``state`` translation keys.
    """
    if coordinator.last_failed_test_time is None:
        return FAILED_STATUS_NEVER

    return FAILED_STATUS_FAILED


SENSOR_DESCRIPTIONS: tuple[BticinoSensorDescription, ...] = (
    BticinoSensorDescription(
        key="health_status",
        icon="mdi:heart-pulse",
        # The overall status is the primary indicator for the device, so it is
        # kept out of the diagnostic category. It reports "offline" as its own
        # state, so it stays available while the device is unreachable.
        entity_category=None,
        device_class=SensorDeviceClass.ENUM,
        options=HEALTH_STATUS_OPTIONS,
        value_fn=_get_health_status,
    ),
    BticinoSensorDescription(
        key="ssh_latency",
        icon="mdi:lan",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda coordinator: coordinator.device_information.ssh_latency_ms,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        requires_connection=True,
    ),
    BticinoSensorDescription(
        key="openwebnet_latency",
        icon="mdi:connection",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda coordinator: coordinator.device_information.openwebnet_latency_ms,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        requires_connection=True,
    ),
    BticinoSensorDescription(
        key="firmware_version",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.firmware_version,
    ),
    BticinoSensorDescription(
        key="firmware_build",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.firmware_build,
    ),
    BticinoSensorDescription(
        key="installed_package",
        icon="mdi:package-variant-closed",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.installed_package,
    ),
    BticinoSensorDescription(
        key="os_release",
        icon="mdi:linux",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.os_release,
    ),
    BticinoSensorDescription(
        key="uptime",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.uptime,
    ),
    BticinoSensorDescription(
        key="hostname",
        icon="mdi:server",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.hostname,
    ),
    BticinoSensorDescription(
        key="mac_address",
        icon="mdi:network-outline",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.device_information.mac_address,
    ),
    BticinoSensorDescription(
        key="last_test_result",
        icon="mdi:check-network-outline",
        device_class=SensorDeviceClass.ENUM,
        options=LAST_TEST_RESULT_OPTIONS,
        value_fn=lambda coordinator: coordinator.last_test_result,
    ),
    BticinoSensorDescription(
        key="last_successful_test",
        icon="mdi:check-circle-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: _parse_timestamp(
            coordinator.last_successful_test_time
        ),
    ),
    BticinoSensorDescription(
        key="last_failed_test_status",
        icon="mdi:alert-circle-outline",
        device_class=SensorDeviceClass.ENUM,
        options=FAILED_STATUS_OPTIONS,
        value_fn=_last_failed_status,
    ),
    BticinoSensorDescription(
        key="last_failed_test",
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
        BticinoClasse100xSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BticinoClasse100xSensor(
    BticinoClasse100xEntity,
    SensorEntity,
):
    """Representation of a BTicino CLASSE100X sensor."""

    entity_description: BticinoSensorDescription

    @property
    def available(self) -> bool:
        """Return whether the sensor has a meaningful value.

        Live measurements are reported as unavailable while the device is
        unreachable, instead of exposing the last (now stale) reading.
        """
        if self.entity_description.requires_connection and not self.coordinator.data:
            return False

        return super().available

    @property
    def native_value(self) -> Any:
        """Return the sensor native value."""
        return self.entity_description.value_fn(self.coordinator)