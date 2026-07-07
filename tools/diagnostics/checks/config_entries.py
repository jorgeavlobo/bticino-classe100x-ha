"""Config entries checks for BTicino CLASSE100X."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result, warning_result
from diagnostics.shared.storage import read_json_file, storage_file


BTICINO_DOMAIN = "bticino_classe100x"
HOMEKIT_DOMAIN = "homekit"
BTICINO_REFERENCE = "bticino_classe100x"


class ConfigEntriesCheck(HealthCheck):
    """Check Home Assistant config entries for BTicino problems."""

    name = "Config Entries"
    description = "Checks BTicino and BTicino-related HomeKit config entries."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the config entries check."""
        path = storage_file(config_path, "core.config_entries")

        if not path.exists():
            return fail_result(
                name=self.name,
                summary="Config entries file was not found.",
                errors=[f"Missing file: {path}"],
            )

        config_entries = read_json_file(path)
        entries = config_entries.get("data", {}).get("entries", [])

        bticino_entries = [
            entry for entry in entries if entry.get("domain") == BTICINO_DOMAIN
        ]

        bticino_homekit_entries = [
            entry
            for entry in entries
            if entry.get("domain") == HOMEKIT_DOMAIN
            and BTICINO_REFERENCE in json.dumps(entry, ensure_ascii=False)
        ]

        details = [
            f"BTicino config entries found: {len(bticino_entries)}",
            f"BTicino-related HomeKit bridges found: {len(bticino_homekit_entries)}",
        ]

        if len(bticino_entries) == 0:
            return fail_result(
                name=self.name,
                summary="No BTicino integration config entry was found.",
                errors=["Expected exactly one BTicino config entry, found 0."],
                details=details,
            )

        if len(bticino_entries) > 1:
            return fail_result(
                name=self.name,
                summary="Multiple BTicino integration config entries were found.",
                errors=[
                    f"Expected exactly one BTicino config entry, found {len(bticino_entries)}."
                ],
                details=details,
            )

        if bticino_homekit_entries:
            return warning_result(
                name=self.name,
                summary="BTicino-related HomeKit bridges were found.",
                warnings=[
                    "HomeKit bridges are not necessarily a problem, but they may contain stale entity references."
                ],
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Config entries look healthy.",
            details=details,
        )