"""BTicino CLASSE100X integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import BticinoClasse100xCoordinator
from .device import async_update_device_registry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


ENTITY_ID_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("button", "condominium_gate", "button.bticino_classe100x_condominium_gate"),
    ("button", "pedestrian_door", "button.bticino_classe100x_pedestrian_door"),
    ("button", "test_ssh_connection", "button.bticino_classe100x_test_ssh_connection"),
    ("binary_sensor", "connection", "binary_sensor.bticino_classe100x_connection_status"),
    ("sensor", "health_status", "sensor.bticino_classe100x_health_status"),
    ("sensor", "ssh_latency", "sensor.bticino_classe100x_ssh_latency"),
    ("sensor", "openwebnet_latency", "sensor.bticino_classe100x_openwebnet_latency"),
    ("sensor", "firmware_version", "sensor.bticino_classe100x_firmware_version"),
    ("sensor", "os_release", "sensor.bticino_classe100x_os_release"),
    ("sensor", "uptime", "sensor.bticino_classe100x_uptime"),
    ("sensor", "hostname", "sensor.bticino_classe100x_hostname"),
    ("sensor", "mac_address", "sensor.bticino_classe100x_mac_address"),
    ("sensor", "last_test_result", "sensor.bticino_classe100x_last_test_result"),
    ("sensor", "last_successful_test", "sensor.bticino_classe100x_last_successful_test"),
    ("sensor", "last_failed_test_status", "sensor.bticino_classe100x_last_failed_status"),
    ("sensor", "last_failed_test", "sensor.bticino_classe100x_last_failed_test"),
)


async def _async_migrate_entity_ids(hass: HomeAssistant, host: str) -> None:
    """Rename BTicino entity IDs to clean, area-independent IDs."""
    registry = er.async_get(hass)

    for domain, unique_key, target_entity_id in ENTITY_ID_TARGETS:
        unique_id = f"{DOMAIN}_{host}_{unique_key}"
        current_entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)

        if current_entity_id is None:
            continue

        if current_entity_id == target_entity_id:
            continue

        if registry.async_get(target_entity_id) is not None:
            _LOGGER.warning(
                "Cannot rename BTicino entity %s to %s because target already exists",
                current_entity_id,
                target_entity_id,
            )
            continue

        _LOGGER.info(
            "Renaming BTicino entity %s to %s",
            current_entity_id,
            target_entity_id,
        )
        registry.async_update_entity(current_entity_id, new_entity_id=target_entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BTicino CLASSE100X from a config entry."""
    coordinator = BticinoClasse100xCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Entity IDs are generated only after platforms are loaded.
    # Therefore migration must run after async_forward_entry_setups().
    host = entry.data[CONF_HOST]
    await _async_migrate_entity_ids(hass, host)

    # Home Assistant only reads device_info when an entity is first added, so
    # details discovered on a later poll (for example the MAC address when the
    # device was unreachable at startup) would otherwise never reach the device
    # registry. Keep the device entry updated as new information arrives.
    async_update_device_registry(hass, coordinator, host)
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: async_update_device_registry(hass, coordinator, host)
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BTicino CLASSE100X config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok