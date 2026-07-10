"""Device helpers for BTicino CLASSE100X."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)

from .const import DOMAIN
from .coordinator import BticinoClasse100xCoordinator

DEVICE_MANUFACTURER = "BTicino"
# Used only until the first successful poll reads the real model from the device
# (``webserver_type`` in dbfiles_ws.xml). Kept so the device page still shows a
# sensible model when the CLASSE100X is unreachable at startup.
DEVICE_MODEL_FALLBACK = "CLASSE100X"
DEVICE_NAME = "BTicino CLASSE100X"


def _resolve_sw_version(
    coordinator: BticinoClasse100xCoordinator,
) -> str | None:
    """Return the software version.

    Prefer the semantic firmware version (for example ``1.5.8``); fall back to
    the formatted build timestamp, then to the raw kernel string, so the device
    page still shows something useful before the first successful poll.
    """
    device_information = coordinator.device_information
    return (
        device_information.firmware_version
        or device_information.firmware_build
        or device_information.kernel
    )


def build_device_info(
    coordinator: BticinoClasse100xCoordinator,
    host: str,
) -> DeviceInfo:
    """Build shared Home Assistant device information.

    Only non-sensitive, stable data is exposed on the device page. SSH
    credentials, private key paths and other internal configuration are never
    included.

    The identifiers are derived from the configured host and never change, which
    keeps the device stable across restarts and preserves the association with
    existing entities. Fields that are not currently available (for example when
    the device is unreachable) are omitted so the device page degrades
    gracefully instead of showing empty values.
    """
    # Prefer the real model discovered from the device; fall back to the constant
    # when the device has not been polled yet (for example offline at startup).
    model = coordinator.device_information.model or DEVICE_MODEL_FALLBACK

    device_info = DeviceInfo(
        identifiers={(DOMAIN, host)},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=model,
        configuration_url=f"http://{host}",
    )

    # Firmware is reported as the Home Assistant software version. Fall back to
    # the kernel string when the firmware version cannot be determined.
    sw_version = _resolve_sw_version(coordinator)
    if sw_version:
        device_info["sw_version"] = sw_version

    # Expose the MAC address using the standard network-connection format so
    # Home Assistant can correlate the device across integrations. The address
    # is only available after a successful device information collection.
    mac_address = coordinator.device_information.mac_address
    if mac_address:
        device_info["connections"] = {
            (CONNECTION_NETWORK_MAC, format_mac(mac_address))
        }

    return device_info


@callback
def async_update_device_registry(
    hass: HomeAssistant,
    coordinator: BticinoClasse100xCoordinator,
    host: str,
) -> None:
    """Apply late-discovered device details to the device registry.

    Home Assistant reads ``device_info`` only when each entity is first added.
    When the CLASSE100X is unreachable at startup, the MAC address, firmware
    version and model are not yet known, so they are missing (or fall back to a
    constant) on the device page. Once a later successful poll discovers them,
    update the existing device entry so the information (and MAC-based
    correlation) appears without requiring a reload.

    The update is idempotent: nothing is written when the registry already holds
    the current values.

    A MAC connection is only merged when no other device already owns it. This
    avoids a ``DeviceConnectionCollisionError`` (which would repeat on every
    poll) when a separate integration, such as a router, has already registered
    the same MAC. In that situation Home Assistant merges the devices through the
    normal ``device_info`` path when the CLASSE100X is reachable at startup.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, host)})
    if device is None:
        return

    changes: dict[str, Any] = {}

    mac_address = coordinator.device_information.mac_address
    if mac_address:
        connection = (CONNECTION_NETWORK_MAC, format_mac(mac_address))
        if connection not in device.connections:
            owner = device_registry.async_get_device(connections={connection})
            if owner is None or owner.id == device.id:
                changes["merge_connections"] = {connection}

    sw_version = _resolve_sw_version(coordinator)
    if sw_version and device.sw_version != sw_version:
        changes["sw_version"] = sw_version

    model = coordinator.device_information.model
    if model and device.model != model:
        changes["model"] = model

    if not changes:
        return

    device_registry.async_update_device(device.id, **changes)
