"""Device helpers for BTicino CLASSE100X."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import BticinoClasse100xCoordinator


def build_device_info(
    coordinator: BticinoClasse100xCoordinator,
    host: str,
) -> DeviceInfo:
    """Build shared Home Assistant device information."""
    device_information = coordinator.device_information

    return DeviceInfo(
        identifiers={(DOMAIN, host)},
        name="BTicino CLASSE100X",
        manufacturer="BTicino",
        model="CLASSE100X",
        sw_version=device_information.firmware_version or device_information.kernel,
        configuration_url=f"http://{host}",
    )
