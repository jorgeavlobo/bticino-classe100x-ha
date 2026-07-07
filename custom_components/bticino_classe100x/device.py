"""Device helpers for BTicino CLASSE100X."""

from __future__ import annotations

from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)

from .const import DOMAIN
from .coordinator import BticinoClasse100xCoordinator

DEVICE_MANUFACTURER = "BTicino"
DEVICE_MODEL = "CLASSE100X"
DEVICE_NAME = "BTicino CLASSE100X"


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
    device_information = coordinator.device_information

    device_info = DeviceInfo(
        identifiers={(DOMAIN, host)},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        configuration_url=f"http://{host}",
    )

    # Firmware is reported as the Home Assistant software version. Fall back to
    # the kernel string when the firmware version cannot be determined.
    sw_version = device_information.firmware_version or device_information.kernel
    if sw_version:
        device_info["sw_version"] = sw_version

    # Expose the MAC address using the standard network-connection format so
    # Home Assistant can correlate the device across integrations. The address
    # is only available after a successful device information collection.
    mac_address = device_information.mac_address
    if mac_address:
        device_info["connections"] = {
            (CONNECTION_NETWORK_MAC, format_mac(mac_address))
        }

    return device_info
