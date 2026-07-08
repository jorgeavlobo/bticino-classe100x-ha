#!/usr/bin/env python3
"""Self-test for the BTicino translation comparison logic.

Exercises the public comparison helpers in ``tools/shared/translations.py``
(``compare``, ``order_notes``, ``canonical_issues``) — the same ones the CLI
validator uses — against synthetic fixtures, asserting they detect each class of
drift the validator promises to catch: missing keys, unexpected keys, type
mismatches, placeholder mismatches, and (informational) key-order differences.

It does not import Home Assistant, so it runs anywhere:

    python3 scripts/validate_translations.py

Exit code ``0`` means every assertion held. The real translation files are
validated separately by ``tools/translations/validate_translations.py``.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from shared.translations import (
    canonical_issues,
    compare,
    flatten_keys,
    order_notes,
    placeholders,
)

REFERENCE = {
    "config": {"title": "BTicino", "note": "Connect to {host}"},
    "entity": {"sensor": {"health": {"name": "Health"}}},
}


def _has(issues: list[str], needle: str) -> bool:
    """Return true if any issue mentions the needle."""
    return any(needle in issue for issue in issues)


def main() -> int:
    """Run every assertion and report the outcome."""
    checks: list[tuple[str, bool]] = []

    # An identical copy has no issues and no order notes.
    identical = {
        "config": {"title": "BTicino", "note": "Connect to {host}"},
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    checks.append(("identical locale has no issues", compare(REFERENCE, identical) == []))
    checks.append(("identical locale has no order notes", order_notes(REFERENCE, identical) == []))

    # A missing leaf key is reported with its dotted path.
    missing = {
        "config": {"title": "BTicino", "note": "Verbinden mit {host}"},
        "entity": {"sensor": {"health": {}}},
    }
    missing_issues = compare(REFERENCE, missing)
    checks.append(("missing key detected", _has(missing_issues, "missing key: entity.sensor.health.name")))

    # An unexpected key present only in the candidate is reported.
    unexpected = {
        "config": {"title": "BTicino", "note": "Connect to {host}", "extra": "x"},
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    checks.append(
        ("unexpected key detected", _has(compare(REFERENCE, unexpected), "unexpected key: config.extra"))
    )

    # A leaf that becomes an object (or vice versa) is a type mismatch.
    type_mismatch = {
        "config": "BTicino",
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    checks.append(
        ("type mismatch detected", _has(compare(REFERENCE, type_mismatch), "type mismatch at config"))
    )

    # When an object is expected but the candidate is a non-string leaf (list,
    # number, null), the reported type is the actual type, not "string".
    checks.append(
        (
            "object-vs-list mismatch reports real type",
            _has(compare({"a": {"b": "x"}}, {"a": [1, 2]}), "type mismatch at a: expected object, got list"),
        )
    )

    # A leaf that stops being a string (null/number/bool) is a type mismatch,
    # even though it has no placeholders to compare.
    non_string_leaf = {
        "config": {"title": "BTicino", "note": "Connect to {host}"},
        "entity": {"sensor": {"health": {"name": 123}}},
    }
    checks.append(
        (
            "non-string leaf detected",
            _has(
                compare(REFERENCE, non_string_leaf),
                "type mismatch at entity.sensor.health.name: expected string, got int",
            ),
        )
    )

    # The reverse: a non-string leaf in the canonical reference itself (a broken
    # en.json) must be flagged, not silently passed.
    checks.append(
        (
            "non-string reference leaf detected",
            _has(
                compare({"a": 123}, {"a": "translated"}),
                "invalid reference value at a: en.json must use string values, got int",
            ),
        )
    )

    # The canonical self-check validates en.json's own leaf types (fail fast),
    # independent of any locale comparison.
    checks.append(("valid canonical has no issues", canonical_issues(REFERENCE) == []))
    checks.append(
        (
            "canonical non-string leaf detected",
            _has(
                canonical_issues({"entity": {"sensor": {"health": {"name": None}}}}),
                "non-string value at entity.sensor.health.name: got NoneType",
            ),
        )
    )

    # A dropped placeholder in a translated value is reported.
    dropped_placeholder = {
        "config": {"title": "BTicino", "note": "Verbindung fehlgeschlagen"},
        "entity": {"sensor": {"health": {"name": "Zustand"}}},
    }
    checks.append(
        (
            "missing placeholder detected",
            _has(compare(REFERENCE, dropped_placeholder), "missing placeholder(s) ['{host}'] at config.note"),
        )
    )

    # Dropping one of a repeated placeholder is detected (multiset comparison,
    # not a plain set): en has {host} twice, the candidate only once.
    repeated_placeholder = {
        "config": {"title": "BTicino", "note": "{host} then {host}"},
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    dropped_repeat = {
        "config": {"title": "BTicino", "note": "{host} then done"},
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    checks.append(
        (
            "dropped repeated placeholder detected",
            _has(compare(repeated_placeholder, dropped_repeat), "missing placeholder(s) ['{host}'] at config.note"),
        )
    )

    # An added placeholder that the source does not have is reported.
    added_placeholder = {
        "config": {"title": "BTicino {brand}", "note": "Connect to {host}"},
        "entity": {"sensor": {"health": {"name": "Health"}}},
    }
    checks.append(
        (
            "unexpected placeholder detected",
            _has(compare(REFERENCE, added_placeholder), "unexpected placeholder(s) ['{brand}'] at config.title"),
        )
    )

    # Reordered but otherwise identical keys are consistent (no issues) yet
    # produce an informational order note.
    reordered = {
        "entity": {"sensor": {"health": {"name": "Health"}}},
        "config": {"note": "Connect to {host}", "title": "BTicino"},
    }
    checks.append(("reordered locale has no issues", compare(REFERENCE, reordered) == []))
    checks.append(("reordered locale is noted", bool(order_notes(REFERENCE, reordered))))

    # The shared helpers behave as the validator relies on.
    checks.append(("placeholders extracts tokens", placeholders("a {x} b {y}") == {"{x}", "{y}"}))
    checks.append(("placeholders ignores non-strings", placeholders(42) == set()))
    checks.append(
        (
            "flatten_keys yields dotted leaves",
            flatten_keys(REFERENCE) == {"config.title", "config.note", "entity.sensor.health.name"},
        )
    )

    ok = True
    for label, passed in checks:
        print(f"{'OK' if passed else 'FAIL'}: {label}")
        ok = ok and passed

    if ok:
        print(f"\nAll {len(checks)} translation-validator assertions passed.")
        return 0

    print("\nTranslation-validator self-test failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
