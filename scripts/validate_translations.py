#!/usr/bin/env python3
"""Validate BTicino CLASSE100X translation completeness.

``strings.json`` is the English source of truth. Every language file under
``translations/`` must expose exactly the same set of keys, so a new string
(for example an added enum sensor ``state`` slug) cannot be shipped in one
language while silently missing in another.

The check is deliberately dependency-free: it flattens each file the same way
Home Assistant's ``recursive_flatten`` helper does and compares the resulting
key sets. Run it locally or in CI:

    python3 scripts/validate_translations.py

Exit code ``0`` means every language matches ``strings.json``; ``1`` means a
file is missing, invalid, or its keys drift from the source.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "bticino_classe100x"
STRINGS = COMPONENT / "strings.json"
TRANSLATIONS = COMPONENT / "translations"


def recursive_flatten(prefix: str, data: dict) -> dict[str, str]:
    """Flatten nested translation data exactly like Home Assistant does."""
    output: dict[str, str] = {}
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

    return set(recursive_flatten("", data))


def main() -> int:
    """Validate that every language file matches strings.json."""
    source = load_keys(STRINGS)
    if source is None:
        print(f"ERROR: missing or invalid source of truth: {STRINGS}")
        return 1

    language_files = sorted(TRANSLATIONS.glob("*.json"))
    if not language_files:
        print(f"ERROR: no language files found in {TRANSLATIONS}")
        return 1

    ok = True
    for path in language_files:
        keys = load_keys(path)
        if keys is None:
            ok = False
            continue

        missing = source - keys
        extra = keys - source
        if missing or extra:
            ok = False
            print(f"FAIL: {path.name} does not match strings.json")
            for key in sorted(missing):
                print(f"  missing: {key}")
            for key in sorted(extra):
                print(f"  extra:   {key}")
        else:
            print(f"OK: {path.name} ({len(keys)} keys)")

    if ok:
        print(f"\nAll {len(language_files)} language file(s) match strings.json.")
        return 0

    print("\nTranslation validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
