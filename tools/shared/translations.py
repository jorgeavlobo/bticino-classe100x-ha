"""Shared translation constants and helpers.

English (``custom_components/bticino_classe100x/translations/en.json``) is the
authoritative source for the BTicino integration; every other locale must expose
exactly the same structure. This is
the single source of truth for the set of locales the integration ships and for
flattening/parsing translation JSON, shared by both the standalone validator
(``tools/translations/validate_translations.py``) and the diagnostics health
check (``tools/diagnostics/checks/translations.py``) so the two never drift.
"""

from __future__ import annotations

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
