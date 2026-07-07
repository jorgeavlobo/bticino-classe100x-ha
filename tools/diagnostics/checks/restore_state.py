"""Restore state checks for BTicino CLASSE100X."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, pass_result, warning_result
from diagnostics.shared.storage import read_json_file, storage_file


BTICINO_REFERENCE = "bticino_classe100x"

DEPRECATED_ENTITY_ID_PARTS: tuple[str, ...] = (
    "entrance_hall_bticino_classe100x",
)


class RestoreStateCheck(HealthCheck):
    """Check Home Assistant restore state for stale BTicino entries."""

    name = "Restore State"
    description = "Checks stale BTicino entries inside core.restore_state."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the restore state check."""
        path = storage_file(config_path, "core.restore_state")

        if not path.exists():
            return pass_result(
                name=self.name,
                summary="Restore state file does not exist.",
                details=["No restore state file found."],
            )

        restore_state = read_json_file(path)
        entries = restore_state.get("data", [])

        bticino_entries = _find_bticino_restore_entries(entries)
        deprecated_entries = [
            entry
            for entry in bticino_entries
            if any(part in _entity_id(entry) for part in DEPRECATED_ENTITY_ID_PARTS)
        ]

        unknown_entries = [
            entry
            for entry in bticino_entries
            if _state(entry) in ("unknown", "unavailable")
        ]

        details = [
            f"BTicino restore entries found: {len(bticino_entries)}",
            f"Deprecated restore entries: {len(deprecated_entries)}",
            f"Unknown/unavailable BTicino restore entries: {len(unknown_entries)}",
        ]

        warnings: list[str] = []

        if deprecated_entries:
            warnings.append("Deprecated BTicino restore entries were found:")
            warnings.extend(f"  {_entity_id(entry)}" for entry in deprecated_entries)

        if unknown_entries:
            warnings.append("Unknown or unavailable BTicino restore entries were found:")
            warnings.extend(f"  {_entity_id(entry)}" for entry in unknown_entries)

        if warnings:
            return warning_result(
                name=self.name,
                summary="Restore state contains stale or unavailable BTicino entries.",
                warnings=warnings,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Restore state looks healthy.",
            details=details,
        )


def _find_bticino_restore_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return BTicino-related restore state entries."""
    return [
        entry
        for entry in entries
        if BTICINO_REFERENCE in _entity_id(entry)
    ]


def _entity_id(entry: dict[str, Any]) -> str:
    """Return the entity_id from a restore state entry."""
    return str(entry.get("state", {}).get("entity_id", ""))


def _state(entry: dict[str, Any]) -> str:
    """Return the state value from a restore state entry."""
    return str(entry.get("state", {}).get("state", ""))