#!/usr/bin/env python3
"""Validate BTicino CLASSE100X translation completeness.

Home Assistant loads a custom integration's translations from
``translations/<language>.json`` at runtime, so ``translations/en.json`` is the
canonical English source. Every other language file must expose exactly the same
set of keys, so a new string (for example an added enum sensor ``state`` slug)
cannot be shipped in one language while silently missing in another.

The check is deliberately dependency-free: it flattens each file the same way
Home Assistant's ``recursive_flatten`` helper does and compares the resulting
key sets. Run it locally or in CI:

    python3 scripts/validate_translations.py

Exit code ``0`` means every language matches ``en.json``; ``1`` means a file is
missing, invalid, or its keys drift from the source.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "bticino_classe100x"
TRANSLATIONS = COMPONENT / "translations"
SOURCE = TRANSLATIONS / "en.json"

# Locales that must always ship. Kept in sync with REQUIRED_TRANSLATIONS in
# tools/diagnostics/checks/translations.py so an accidentally deleted locale
# fails CI instead of being silently skipped.
REQUIRED_LOCALES = ("en.json", "fr.json", "pt.json")


def recursive_flatten(prefix: str, data: dict) -> dict[str, object]:
    """Flatten nested translation data exactly like Home Assistant does.

    Only the keys are used by this validator; leaf values are returned as-is and
    are not assumed to be strings.
    """
    output: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            output.update(recursive_flatten(f"{prefix}{key}.", value))
        else:
            output[f"{prefix}{key}"] = value
    return output


def load_keys(path: Path) -> set[str] | None:
    """Return the flattened key set for a translation file, or None on error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read {path.name}: {exc}")
        return None

    if not isinstance(data, dict):
        print(f"ERROR: {path.name} must contain a JSON object, got {type(data).__name__}")
        return None

    return set(recursive_flatten("", data))


def main() -> int:
    """Validate that every language file matches en.json."""
    source = load_keys(SOURCE)
    if source is None:
        print(f"ERROR: missing or invalid source of truth: {SOURCE}")
        return 1

    language_files = sorted(TRANSLATIONS.glob("*.json"))
    if not language_files:
        print(f"ERROR: no language files found in {TRANSLATIONS}")
        return 1

    ok = True

    present = {path.name for path in language_files}
    for name in REQUIRED_LOCALES:
        if name not in present:
            ok = False
            print(f"FAIL: required translation file is missing: {name}")

    for path in language_files:
        keys = load_keys(path)
        if keys is None:
            ok = False
            continue

        missing = source - keys
        extra = keys - source
        if missing or extra:
            ok = False
            print(f"FAIL: {path.name} does not match {SOURCE.name}")
            for key in sorted(missing):
                print(f"  missing: {key}")
            for key in sorted(extra):
                print(f"  extra:   {key}")
        else:
            print(f"OK: {path.name} ({len(keys)} keys)")

    if ok:
        print(f"\nAll {len(language_files)} language file(s) match {SOURCE.name}.")
        return 0

    print("\nTranslation validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
