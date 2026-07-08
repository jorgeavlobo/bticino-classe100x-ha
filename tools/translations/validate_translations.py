#!/usr/bin/env python3
"""Validate BTicino CLASSE100X translation completeness and consistency.

English (``custom_components/bticino_classe100x/translations/en.json``) is the
authoritative source. Every other locale must expose exactly the same keys, JSON
hierarchy, value types and ``{placeholder}`` tokens, so a string cannot ship in
one language while missing, drifting or losing a placeholder in another.

The check is deliberately dependency-free (no Home Assistant import), so it runs
anywhere:

    python3 tools/translations/validate_translations.py

It first validates the canonical file itself (every leaf must be a string), then
for each locale reports missing keys, unexpected keys, type mismatches (object
vs string, or a non-string leaf) and placeholder mismatches. Key-order
differences are reported as informational notes only and never affect the
outcome. The files are never modified.

Exit code ``0`` means every locale matches the canonical file; ``1`` means a
required locale is missing, a file is invalid JSON, the canonical file has an
invalid value type, or a locale drifts from the source.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

# Make the shared ``tools`` packages importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.translations import (  # noqa: E402  (path set up above)
    CANONICAL_LOCALE,
    REQUIRED_LOCALES,
    canonical_issues,
    compare,
    order_notes,
)

# The repo-relative directory holding the translation files, used for display so
# the tool's output names paths that actually exist in the repository.
DISPLAY_DIR = "custom_components/bticino_classe100x/translations"

TRANSLATIONS = Path(__file__).resolve().parents[2] / Path(DISPLAY_DIR)


def _load(path: Path) -> dict[str, Any] | None:
    """Return the parsed JSON object, or None (after printing why) on error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"    ERROR: could not read {path.name}: {exc}")
        return None
    if not isinstance(data, dict):
        print(f"    ERROR: {path.name} must be a JSON object, got {type(data).__name__}")
        return None
    return data


def main() -> int:
    """Validate every locale against the canonical file and report the outcome."""
    print("Validating BTicino translations...\n")
    print(f"Reference: {DISPLAY_DIR}/{CANONICAL_LOCALE}\n")

    source_path = TRANSLATIONS / CANONICAL_LOCALE
    if not source_path.is_file():
        print(f"ERROR: missing source of truth: {DISPLAY_DIR}/{CANONICAL_LOCALE}")
        return 1
    reference = _load(source_path)
    if reference is None:
        return 1

    # Validate the canonical file itself before comparing anything against it, so
    # an invalid en.json fails fast instead of silently defining the contract.
    print(f"{DISPLAY_DIR}/{CANONICAL_LOCALE}")
    canonical = canonical_issues(reference)
    if canonical:
        print("  FAILED (invalid canonical file)")
        for issue in canonical:
            print(f"    {issue}")
        print("\nTranslation validation failed.")
        return 1
    print("  PASS (reference)\n")

    locale_files = sorted(TRANSLATIONS.glob("*.json"))
    present = {path.name for path in locale_files}

    ok = True

    for name in REQUIRED_LOCALES:
        if name not in present:
            ok = False
            print(f"FAIL: required locale is missing: {name}")

    for path in locale_files:
        if path.name == CANONICAL_LOCALE:
            continue

        print(f"{DISPLAY_DIR}/{path.name}")

        candidate = _load(path)
        if candidate is None:
            ok = False
            print("  FAILED\n")
            continue

        issues = compare(reference, candidate)
        if issues:
            ok = False
            print("  FAILED")
            for issue in issues:
                print(f"    {issue}")
        else:
            print("  PASS")

        for note in order_notes(reference, candidate):
            print(f"    note: {note}")
        print()

    if ok:
        compared = sum(1 for path in locale_files if path.name != CANONICAL_LOCALE)
        print(
            f"{CANONICAL_LOCALE} is valid and all {compared} other locale(s) "
            f"are consistent with it."
        )
        return 0

    print("Translation validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
