"""Diagnostics support for BTicino CLASSE100X.

Diagnostics are designed to be safe to attach to public GitHub issues. Every
installation-specific value is redacted through :mod:`.sanitize`; this module
never redacts inline. The privacy policy for each field is:

- **Visible** (safe to expose): integration/Home Assistant version, entity
  count, platforms, entry title/id/version/source, auth method, the
  ``*_configured``/``*_exists`` booleans, command timeout, release delay,
  connection/coordinator status, test timestamps and results, firmware version,
  firmware build, model, installed package, OS release, uptime and the
  SSH/OpenWebNet latencies.
- **Partially redacted**: MAC address (vendor OUI kept), hostname (model prefix
  kept), kernel (version kept, node name dropped), last error (secrets removed).
- **Fully redacted**: host (only the address family is kept) and username.
- **Never included**: passwords, SSH private key contents and the private key
  path.
"""

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

from ..const import (
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
from .sanitize import (
    sanitize_error,
    sanitize_host,
    sanitize_hostname,
    sanitize_kernel,
    sanitize_mac,
    sanitize_username,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Only non-sensitive information is exposed. Installation-specific values are
    redacted through :mod:`.sanitize`, and passwords and private key contents
    are never included. The output degrades gracefully when the device is
    offline or some device information is unavailable.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    # Mirror the coordinator: options override the original config entry data,
    # so read connection settings (and the values used for redaction) from the
    # merged mapping to avoid reporting or leaking stale values.
    config = {**entry.data, **entry.options}

    host = config.get(CONF_HOST)
    username = config.get(CONF_USERNAME)

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
    platforms = sorted({entity.entity_id.split(".")[0] for entity in entities})

    device_information = getattr(coordinator, "device_information", None)
    hostname = device_information.hostname if device_information else None

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
            "host": sanitize_host(host),
            "username": sanitize_username(username),
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
                sanitize_error(
                    coordinator.last_error,
                    ssh_key_path=ssh_key_path,
                    host=host,
                    hostname=hostname,
                    username=username,
                )
                if coordinator
                else None
            ),
        },
        "device_information": {
            "firmware_version": (
                device_information.firmware_version if device_information else None
            ),
            "firmware_build": (
                device_information.firmware_build if device_information else None
            ),
            "model": device_information.model if device_information else None,
            "installed_package": (
                device_information.installed_package if device_information else None
            ),
            "os_release": device_information.os_release if device_information else None,
            "hostname": sanitize_hostname(hostname),
            "kernel": (
                sanitize_kernel(device_information.kernel, hostname)
                if device_information
                else None
            ),
            "uptime": device_information.uptime if device_information else None,
            "mac_address": (
                sanitize_mac(device_information.mac_address)
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
