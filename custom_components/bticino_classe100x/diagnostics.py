"""Diagnostics support for BTicino CLASSE100X."""

from __future__ import annotations

import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_USERNAME,
    __version__ as HA_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration

from .const import (
    AUTH_METHOD_SSH_KEY,
    CONF_AUTH_METHOD,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_RELEASE_DELAY,
    CONF_SSH_KEY_PATH,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_RELEASE_DELAY,
    DOMAIN,
)


def _sanitize_error(error: str | None, ssh_key_path: str | None) -> str | None:
    """Redact the private key path from an error message.

    Error strings can echo the SSH command, which includes the private key
    path. The path itself is not needed for debugging, so it is replaced with a
    placeholder while the rest of the message is kept.
    """
    if not error or not ssh_key_path:
        return error

    return error.replace(ssh_key_path, "<ssh_key_path>")


def _redact_mac(mac_address: str | None) -> str | None:
    """Mask the device-specific half of a MAC address.

    Diagnostics are meant to be shared in issue reports, so only the vendor
    prefix (OUI) is kept for debugging while the unique portion is hidden to
    avoid publishing a stable device identifier.
    """
    if not mac_address:
        return mac_address

    parts = mac_address.split(":")
    if len(parts) != 6:
        return mac_address

    return ":".join([*parts[:3], "**", "**", "**"])


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Only non-sensitive information is exposed: passwords, private key contents
    and the private key path are never included, and the last error has the key
    path redacted. The output degrades gracefully when the device is offline or
    some device information is unavailable.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    # Mirror the coordinator: options override the original config entry data,
    # so read connection settings (and the key path used for redaction) from the
    # merged mapping to avoid reporting or leaking stale values.
    config = {**entry.data, **entry.options}

    ssh_key_path = config.get(CONF_SSH_KEY_PATH)
    ssh_key_exists = False

    if ssh_key_path:
        ssh_key_exists = await hass.async_add_executor_job(
            os.path.isfile,
            ssh_key_path,
        )

    integration = await async_get_integration(hass, DOMAIN)

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    platforms = sorted({entity.domain for entity in entities})

    device_information = getattr(coordinator, "device_information", None)

    return {
        "integration": {
            "domain": DOMAIN,
            "version": str(integration.version) if integration.version else None,
            "home_assistant_version": HA_VERSION,
            "entity_count": len(entities),
            "platforms": platforms,
        },
        "entry": {
            "title": entry.title,
            "entry_id": entry.entry_id,
            "version": entry.version,
            "source": entry.source,
        },
        "connection": {
            "host": config.get(CONF_HOST),
            "username": config.get(CONF_USERNAME),
            "auth_method": config.get(CONF_AUTH_METHOD, AUTH_METHOD_SSH_KEY),
            "ssh_key_configured": bool(ssh_key_path),
            "ssh_key_exists": ssh_key_exists,
            "password_configured": bool(config.get(CONF_PASSWORD)),
            "command_timeout": config.get(
                CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT
            ),
            "release_delay": config.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY),
        },
        "status": {
            "connected": bool(coordinator.data) if coordinator else None,
            "last_update_success": (
                coordinator.last_update_success if coordinator else None
            ),
            "last_test_result": coordinator.last_test_result if coordinator else None,
            "last_test_time": coordinator.last_test_time if coordinator else None,
            "last_successful_test_time": (
                coordinator.last_successful_test_time if coordinator else None
            ),
            "last_failed_test_time": (
                coordinator.last_failed_test_time if coordinator else None
            ),
            "last_error": (
                _sanitize_error(coordinator.last_error, ssh_key_path)
                if coordinator
                else None
            ),
        },
        "device_information": {
            "firmware_version": (
                device_information.firmware_version if device_information else None
            ),
            "os_release": device_information.os_release if device_information else None,
            "hostname": device_information.hostname if device_information else None,
            "kernel": device_information.kernel if device_information else None,
            "uptime": device_information.uptime if device_information else None,
            "mac_address": (
                _redact_mac(device_information.mac_address)
                if device_information
                else None
            ),
            "ssh_latency_ms": (
                device_information.ssh_latency_ms if device_information else None
            ),
            "openwebnet_latency_ms": (
                device_information.openwebnet_latency_ms if device_information else None
            ),
        },
    }
