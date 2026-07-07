"""Device registry checks for BTicino CLASSE100X."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file, storage_file


BTICINO_REFERENCE = "bticino_classe100x"


class DeviceRegistryCheck(HealthCheck):
    """Check Home Assistant device registry for BTicino devices."""

    name = "Device Registry"
    description = "Checks BTicino devices in the Home Assistant device registry."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the device registry check."""
        path = storage_file(config_path, "core.device_registry")

        if not path.exists():
            return fail_result(
                name=self.name,
                summary="Device registry file was not found.",
                errors=[f"Missing file: {path}"],
            )

        device_registry = read_json_file(path)
        devices = device_registry.get("data", {}).get("devices", [])

        bticino_devices = [
            device
            for device in devices
            if BTICINO_REFERENCE in json.dumps(device, ensure_ascii=False)
        ]

        details = [
            f"BTicino devices found: {len(bticino_devices)}",
        ]

        if len(bticino_devices) == 0:
            return fail_result(
                name=self.name,
                summary="No BTicino device was found.",
                errors=["Expected at least one BTicino device."],
                details=details,
            )

        if len(bticino_devices) > 1:
            return fail_result(
                name=self.name,
                summary="Multiple BTicino devices were found.",
                errors=[f"Expected one BTicino device, found {len(bticino_devices)}."],
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Device registry looks healthy.",
            details=details,
        )