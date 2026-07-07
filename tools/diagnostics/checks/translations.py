"""Translation checks for BTicino CLASSE100X."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diagnostics.shared.check import HealthCheck
from diagnostics.shared.result import HealthCheckResult, fail_result, pass_result
from diagnostics.shared.storage import read_json_file


TRANSLATION_FOLDER = Path("custom_components/bticino_classe100x/translations")

REQUIRED_TRANSLATIONS: tuple[str, ...] = (
    "en.json",
    "fr.json",
    "pt.json",
)


class TranslationsCheck(HealthCheck):
    """Check translation files."""

    name = "Translations"
    description = "Checks BTicino translation files and key consistency."

    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the translations check."""
        folder = _find_translation_folder(config_path)

        if folder is None:
            return fail_result(
                name=self.name,
                summary="Translation folder was not found.",
                errors=["Could not find custom_components/bticino_classe100x/translations."],
            )

        errors: list[str] = []
        details: list[str] = []

        loaded: dict[str, dict[str, Any]] = {}

        for filename in REQUIRED_TRANSLATIONS:
            path = folder / filename

            if not path.exists():
                errors.append(f"Missing translation file: {filename}")
                continue

            loaded[filename] = read_json_file(path)
            details.append(f"Found translation file: {filename}")

        if "en.json" in loaded:
            english_keys = _flatten_keys(loaded["en.json"])

            for filename, data in loaded.items():
                keys = _flatten_keys(data)
                missing_keys = sorted(english_keys - keys)

                if missing_keys:
                    errors.append(f"{filename} is missing keys:")
                    errors.extend(f"  {key}" for key in missing_keys)

        if errors:
            return fail_result(
                name=self.name,
                summary="Translation files contain problems.",
                errors=errors,
                details=details,
            )

        return pass_result(
            name=self.name,
            summary="Translation files look healthy.",
            details=details,
        )


def _find_translation_folder(config_path: Path) -> Path | None:
    """Find translation folder in a Home Assistant config or repository root."""
    home_assistant_folder = config_path / TRANSLATION_FOLDER
    if home_assistant_folder.exists():
        return home_assistant_folder

    repository_folder = Path.cwd() / TRANSLATION_FOLDER
    if repository_folder.exists():
        return repository_folder

    return None


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    """Return flattened dictionary keys."""
    keys: set[str] = set()

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            keys.update(_flatten_keys(value, full_key))
        else:
            keys.add(full_key)

    return keys