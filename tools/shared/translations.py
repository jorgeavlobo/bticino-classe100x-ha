"""Shared translation constants and helpers.

English (``custom_components/bticino_classe100x/translations/en.json``) is the
authoritative source for the BTicino integration; every other locale must expose
exactly the same structure. This is the single source of truth for the set of
locales the integration ships and for the comparison logic (flattening, key/
placeholder/type diffing), shared by the standalone validator
(``tools/translations/validate_translations.py``), its self-test
(``scripts/validate_translations.py``) and the diagnostics health check
(``tools/diagnostics/checks/translations.py``) so they never drift.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

# English is the authoritative source; every other locale must match it.
CANONICAL_LOCALE = "en.json"

# Every locale the integration ships. Listing them here means an accidentally
# deleted locale fails validation instead of silently disappearing.
REQUIRED_LOCALES: tuple[str, ...] = (
    "en.json",
    "fr.json",
    "pt.json",
    "de.json",
    "it.json",
)

# A ``{placeholder}`` token as used by Home Assistant translation strings. The
# inner text has no braces, so nested braces are not matched.
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def flatten_keys(data: Any, prefix: str = "") -> set[str]:
    """Return the set of dotted leaf-key paths in a translation mapping.

    A non-dict input yields an empty set, so a malformed file degrades to "no
    keys" rather than raising.
    """
    keys: set[str] = set()
    if not isinstance(data, dict):
        return keys
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def placeholders(text: Any) -> set[str]:
    """Return the ``{placeholder}`` tokens in a string (empty set for non-str)."""
    if not isinstance(text, str):
        return set()
    return set(_PLACEHOLDER.findall(text))


def placeholder_counts(text: Any) -> Counter[str]:
    """Return a multiset of ``{placeholder}`` tokens (empty for non-str).

    Counting rather than a plain set means dropping one of a repeated
    placeholder (e.g. ``{host} … {host}`` reduced to a single ``{host}``) is
    still detected.
    """
    if not isinstance(text, str):
        return Counter()
    return Counter(_PLACEHOLDER.findall(text))


def canonical_issues(data: dict, path: str = "") -> list[str]:
    """Return type problems in the canonical file itself.

    Every leaf must be a string. A non-string leaf in the canonical source would
    otherwise be silently accepted (``placeholders()`` ignores non-strings), so
    it is validated up front rather than relying on a locale comparison.
    """
    issues: list[str] = []
    for key, value in data.items():
        key_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            issues.extend(canonical_issues(value, key_path))
        elif not isinstance(value, str):
            issues.append(
                f"non-string value at {key_path}: got {type(value).__name__}"
            )
    return issues


def compare(reference: dict, candidate: dict, path: str = "") -> list[str]:
    """Return the structural differences of candidate against reference.

    Detects missing keys, unexpected keys, type mismatches (object vs leaf, or a
    non-string leaf) and placeholder mismatches on string leaves.
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
            issues.extend(compare(ref_value, cand_value, key_path))
        elif ref_is_obj != cand_is_obj:
            expected = "object" if ref_is_obj else "string"
            actual = "object" if cand_is_obj else type(cand_value).__name__
            issues.append(
                f"type mismatch at {key_path}: expected {expected}, got {actual}"
            )
        elif not isinstance(ref_value, str):
            # The canonical leaf itself is not a string (e.g. a value committed
            # as a number or null). Flag the source, since placeholders() ignores
            # non-strings and would otherwise pass.
            issues.append(
                f"invalid reference value at {key_path}: en.json must use "
                f"string values, got {type(ref_value).__name__}"
            )
        elif not isinstance(cand_value, str):
            # A translation value must be a string; a locale that turned a string
            # into null/true/123 would otherwise only be placeholder-checked (and
            # pass) since placeholders() ignores non-strings.
            issues.append(
                f"type mismatch at {key_path}: expected string, got "
                f"{type(cand_value).__name__}"
            )
        else:
            ref_ph = placeholder_counts(ref_value)
            cand_ph = placeholder_counts(cand_value)
            missing_ph = ref_ph - cand_ph
            extra_ph = cand_ph - ref_ph
            if missing_ph:
                issues.append(
                    f"missing placeholder(s) {sorted(missing_ph.elements())} at {key_path}"
                )
            if extra_ph:
                issues.append(
                    f"unexpected placeholder(s) {sorted(extra_ph.elements())} at {key_path}"
                )

    for key in candidate:
        if key not in reference:
            key_path = f"{path}.{key}" if path else key
            issues.append(f"unexpected key: {key_path}")

    return issues


def order_notes(reference: Any, candidate: Any, path: str = "") -> list[str]:
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
            notes.extend(order_notes(reference[key], candidate[key], key_path))

    return notes
