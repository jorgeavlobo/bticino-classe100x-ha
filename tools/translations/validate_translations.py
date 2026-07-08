#!/usr/bin/env python3
"""Validate BTicino CLASSE100X translation completeness and consistency.

English (``translations/en.json``) is the authoritative source. Every other
locale must expose exactly the same keys, JSON hierarchy, value types and
``{placeholder}`` tokens, so a string cannot ship in one language while missing,
drifting or losing a placeholder in another.

The check is deliberately dependency-free (no Home Assistant import), so it runs
anywhere:

    python3 tools/translations/validate_translations.py

For each locale it reports missing keys, unexpected keys, type mismatches
(object vs string) and placeholder mismatches. Key-order differences are
reported as informational notes only and never affect the outcome. The files
are never modified.

Exit code ``0`` means every locale matches ``en.json``; ``1`` means a required
locale is missing, a file is invalid JSON, or a locale drifts from the source.
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
    placeholders,
)

TRANSLATIONS = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "bticino_classe100x"
    / "translations"
)


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


def _compare(reference: dict, candidate: dict, path: str = "") -> list[str]:
    """Return the structural differences of candidate against reference.

    Detects missing keys, unexpected keys, type mismatches (object vs string)
    and placeholder mismatches on string leaves.
    """
    issues: list[str] = []

    for key, ref_value in reference.items():
        key_path = f"{path}.{key}" if path else key

        if key not in candidate:
            issues.append(f"missing key: {key_path}")
            continue

        cand_value = candidate[key]
        ref_is_obj = isinstance(ref_value, dict)
        cand_is_obj = isinstance(cand_value, dict)

        if ref_is_obj and cand_is_obj:
            issues.extend(_compare(ref_value, cand_value, key_path))
        elif ref_is_obj != cand_is_obj:
            expected = "object" if ref_is_obj else "string"
            actual = "object" if cand_is_obj else "string"
            issues.append(
                f"type mismatch at {key_path}: expected {expected}, got {actual}"
            )
        else:
            missing_ph = placeholders(ref_value) - placeholders(cand_value)
            extra_ph = placeholders(cand_value) - placeholders(ref_value)
            if missing_ph:
                issues.append(
                    f"missing placeholder(s) {sorted(missing_ph)} at {key_path}"
                )
            if extra_ph:
                issues.append(
                    f"unexpected placeholder(s) {sorted(extra_ph)} at {key_path}"
                )

    for key in candidate:
        if key not in reference:
            key_path = f"{path}.{key}" if path else key
            issues.append(f"unexpected key: {key_path}")

    return issues


def _order_notes(reference: Any, candidate: Any, path: str = "") -> list[str]:
    """Return informational notes where shared keys are in a different order."""
    notes: list[str] = []
    if not (isinstance(reference, dict) and isinstance(candidate, dict)):
        return notes

    ref_order = [key for key in reference if key in candidate]
    cand_order = [key for key in candidate if key in reference]
    if ref_order != cand_order:
        notes.append(f"key order differs at {path or '(root)'}")

    for key in reference:
        if key in candidate:
            key_path = f"{path}.{key}" if path else key
            notes.extend(_order_notes(reference[key], candidate[key], key_path))

    return notes


def main() -> int:
    """Validate every locale against en.json and report the outcome."""
    print("Validating BTicino translations...\n")
    print(f"Reference: translations/{CANONICAL_LOCALE}\n")

    source_path = TRANSLATIONS / CANONICAL_LOCALE
    if not source_path.is_file():
        print(f"ERROR: missing source of truth: translations/{CANONICAL_LOCALE}")
        return 1
    reference = _load(source_path)
    if reference is None:
        return 1

    locale_files = sorted(TRANSLATIONS.glob("*.json"))
    present = {path.name for path in locale_files}

    ok = True

    for name in REQUIRED_LOCALES:
        if name not in present:
            ok = False
            print(f"FAIL: required locale is missing: {name}")

    for path in locale_files:
        print(f"translations/{path.name}")

        if path.name == CANONICAL_LOCALE:
            print("  PASS (reference)\n")
            continue

        candidate = _load(path)
        if candidate is None:
            ok = False
            print("  FAILED\n")
            continue

        issues = _compare(reference, candidate)
        if issues:
            ok = False
            print("  FAILED")
            for issue in issues:
                print(f"    {issue}")
        else:
            print("  PASS")

        for note in _order_notes(reference, candidate):
            print(f"    note: {note}")
        print()

    if ok:
        print(f"All {len(locale_files)} locale(s) are consistent with {CANONICAL_LOCALE}.")
        return 0

    print("Translation validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
