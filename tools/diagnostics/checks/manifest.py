"""Manifest checks for BTicino CLASSE100X."""

from __future__ import annotations

from pathlib import Path

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file


INTEGRATION_MANIFEST = Path(
    "custom_components/bticino_classe100x/manifest.json"
)


class ManifestCheck(HealthCheck):
    """Check the integration manifest file."""

    name = "Manifest"
    description = "Checks the BTicino integration manifest."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the manifest check."""
        path = _find_manifest_path(config_path)

        if path is None:
            return fail_result(
                name=self.name,
                summary="Manifest file was not found.",
                errors=["Could not find custom_components/bticino_classe100x/manifest.json."],
            )

        manifest = read_json_file(path)

        version = manifest.get("version")
        domain = manifest.get("domain")
        config_flow = manifest.get("config_flow")

        errors: list[str] = []
        details = [
            f"Manifest path: {path}",
            f"Domain: {domain}",
            f"Version: {version}",
            f"Config flow: {config_flow}",
        ]

        if domain != "bticino_classe100x":
            errors.append(f"Unexpected domain: {domain}")

        if not version:
            errors.append("Manifest version is missing.")

        if config_flow is not True:
            errors.append("config_flow should be true.")

        if errors:
            return fail_result(
                name=self.name,
                summary="Manifest contains problems.",
                errors=errors,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Manifest looks healthy.",
            details=details,
        )


def _find_manifest_path(config_path: Path) -> Path | None:
    """Find manifest path in a Home Assistant config or repository root."""
    home_assistant_path = config_path / INTEGRATION_MANIFEST
    if home_assistant_path.exists():
        return home_assistant_path

    repository_path = Path.cwd() / INTEGRATION_MANIFEST
    if repository_path.exists():
        return repository_path

    return None