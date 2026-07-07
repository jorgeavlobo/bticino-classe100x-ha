"""Diagnostics support for BTicino CLASSE100X."""

from __future__ import annotations

import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AUTH_METHOD,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_RELEASE_DELAY,
    CONF_SSH_KEY_PATH,
    DOMAIN,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Sensitive values such as passwords and private key contents are never exposed.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    ssh_key_path = entry.data.get(CONF_SSH_KEY_PATH)
    ssh_key_exists = False

    if ssh_key_path:
        ssh_key_exists = await hass.async_add_executor_job(
            os.path.isfile,
            ssh_key_path,
        )

    device_information = getattr(coordinator, "device_information", None)

    return {
        "entry": {
            "title": entry.title,
            "entry_id": entry.entry_id,
            "version": entry.version,
            "source": entry.source,
        },
        "connection": {
            "host": entry.data.get(CONF_HOST),
            "username": entry.data.get(CONF_USERNAME),
            "auth_method": entry.data.get(CONF_AUTH_METHOD, "ssh_key"),
            "ssh_key_path": ssh_key_path,
            "ssh_key_exists": ssh_key_exists,
            "password_configured": bool(entry.data.get(CONF_PASSWORD)),
            "command_timeout": entry.data.get(CONF_COMMAND_TIMEOUT, 10),
            "release_delay": entry.data.get(CONF_RELEASE_DELAY, 1.0),
        },
        "status": {
            "connected": bool(coordinator.data) if coordinator else None,
            "last_test_result": coordinator.last_test_result if coordinator else None,
            "last_test_time": coordinator.last_test_time if coordinator else None,
            "last_successful_test_time": (
                coordinator.last_successful_test_time if coordinator else None
            ),
            "last_failed_test_time": (
                coordinator.last_failed_test_time if coordinator else None
            ),
            "last_error": coordinator.last_error if coordinator else None,
        },
        "integration": {
            "entity_count": 16,
            "platforms_loaded": ["button", "binary_sensor", "sensor"],
        },
        "device_information": {
            "hostname": device_information.hostname if device_information else None,
            "kernel": device_information.kernel if device_information else None,
            "uptime": device_information.uptime if device_information else None,
            "mac_address": device_information.mac_address if device_information else None,
            "ssh_latency_ms": device_information.ssh_latency_ms if device_information else None,
            "openwebnet_latency_ms": device_information.openwebnet_latency_ms if device_information else None,
            "firmware_version": device_information.firmware_version if device_information else None,
            "os_release": device_information.os_release if device_information else None,
        },
    }
