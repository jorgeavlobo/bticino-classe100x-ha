"""YAML configuration checks for BTicino CLASSE100X."""

from __future__ import annotations

from pathlib import Path

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, pass_result, warning_result


SEARCH_TERMS: tuple[str, ...] = (
    "bticino_classe100x",
    "condominium_gate",
    "pedestrian_door",
)

YAML_FILES: tuple[str, ...] = (
    "configuration.yaml",
    "automations.yaml",
    "scripts.yaml",
    "scenes.yaml",
)


class YamlConfigCheck(HealthCheck):
    """Check YAML configuration files for stale BTicino references."""

    name = "YAML Configuration"
    description = "Checks common YAML files for BTicino references."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the YAML configuration check."""
        matches: list[str] = []

        for filename in YAML_FILES:
            path = config_path / filename

            if not path.exists():
                continue

            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                lowered = line.lower()

                if any(term in lowered for term in SEARCH_TERMS):
                    matches.append(f"{path}:{line_number}: {line.strip()}")

        details = [
            f"YAML matches found: {len(matches)}",
        ]

        if matches:
            return warning_result(
                name=self.name,
                summary="BTicino references were found in YAML configuration files.",
                warnings=matches,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="No BTicino references found in common YAML files.",
            details=details,
        )