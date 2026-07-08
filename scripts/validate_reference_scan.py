#!/usr/bin/env python3
"""Self-test for the BTicino reference detection tools.

Builds a synthetic ``.storage`` fixture and asserts that BTicino references are
detected structurally and HACS-aware:

- a real BTicino config entry, entity, device and dashboard reference are
  confirmed;
- HACS management entities (``update``/``switch``) are reported as informational
  only and never counted as confirmed references or matched for cleanup;
- an unrelated entity that merely mentions a word like "Condominium" is not
  reported.

It does not import Home Assistant, so it runs anywhere:

    python3 scripts/validate_reference_scan.py

Exit code ``0`` means every assertion held.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from diagnostics.find_bticino_references import find_references
from diagnostics.shared.entities import is_bticino_entity
from shared.cli import ToolOptions
from shared.matching import contains_bticino_reference, is_hacs_managed

DOMAIN = "bticino_classe100x"
HOST = "192.168.50.251"

CONFIG_ENTRIES = {
    "data": {
        "entries": [
            {"entry_id": "bt1", "domain": DOMAIN, "data": {"host": HOST}},
            {"entry_id": "hacs1", "domain": "hacs", "data": {}},
            {
                "entry_id": "hk1",
                "domain": "homekit",
                "data": {
                    "entities": [f"button.{DOMAIN}_condominium_gate"],
                },
            },
        ]
    }
}
ENTITY_REGISTRY = {
    "data": {
        "entities": [
            {
                "entity_id": f"sensor.{DOMAIN}_health_status",
                "unique_id": f"{DOMAIN}_{HOST}_health_status",
                "platform": DOMAIN,
                "config_entry_id": "bt1",
            },
            {
                "entity_id": f"update.{DOMAIN}_update",
                "unique_id": f"{DOMAIN}_update",
                "platform": "hacs",
                "config_entry_id": "hacs1",
            },
            {
                "entity_id": f"switch.{DOMAIN}_pre_release",
                "unique_id": f"{DOMAIN}_pre_release",
                "platform": "hacs",
                "config_entry_id": "hacs1",
            },
            {
                "entity_id": "sensor.video_intercom_rx",
                "unique_id": "vi_rx",
                "platform": "other_intercom",
                "config_entry_id": "oth1",
                "original_name": "Condominium Gate Button Pressed",
            },
        ],
        "deleted_entities": [],
    }
}
DEVICE_REGISTRY = {
    "data": {
        "devices": [
            {"id": "dev1", "name": "CLASSE100X", "identifiers": [[DOMAIN, HOST]]},
            {"id": "dev2", "name": "Other", "identifiers": [["other_intercom", "x"]]},
        ],
        "deleted_devices": [],
    }
}
RESTORE_STATE = {
    "data": [
        {"state": {"entity_id": f"sensor.{DOMAIN}_health_status", "state": "healthy"}},
        {"state": {"entity_id": f"update.{DOMAIN}_update", "state": "on"}},
        {
            "state": {
                "entity_id": "sensor.video_intercom_rx",
                "state": "Condominium Gate Button Pressed",
            }
        },
        # Unrelated entity whose STATE text happens to contain the token: the
        # entity_id is what matters, so this must not be reported.
        {
            "state": {
                "entity_id": "sensor.unrelated_note",
                "state": f"see {DOMAIN} docs",
            }
        },
    ]
}
LOVELACE = json.dumps(
    {"cards": [{"entity": f"sensor.{DOMAIN}_health_status"}, {"name": "Condominium Gate"}]}
)
# A dashboard that references only an exact legacy entity id (no integration
# token) must still be reported, matching what the clean tools remove.
LEGACY_DASHBOARD = json.dumps({"cards": [{"entity": "button.condominium_gate"}]})


def _write_fixture(base: Path) -> None:
    storage = base / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "core.config_entries").write_text(json.dumps(CONFIG_ENTRIES), "utf-8")
    (storage / "core.entity_registry").write_text(json.dumps(ENTITY_REGISTRY), "utf-8")
    (storage / "core.device_registry").write_text(json.dumps(DEVICE_REGISTRY), "utf-8")
    (storage / "core.restore_state").write_text(json.dumps(RESTORE_STATE), "utf-8")
    (storage / "lovelace").write_text(LOVELACE, "utf-8")
    (storage / "lovelace.legacy").write_text(LEGACY_DASHBOARD, "utf-8")


def _scan() -> tuple[object, str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        _write_fixture(base)
        buffer = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buffer
        try:
            result = find_references(ToolOptions(config_path=base))
        finally:
            sys.stdout = stdout
    return result, buffer.getvalue()


def main() -> int:
    """Run every assertion and report the outcome."""
    checks: list[tuple[str, bool]] = []

    result, output = _scan()
    checks.append(("scan completed", result.storage_found and result.unreadable == 0))
    checks.append(("no video_intercom false positive", "video_intercom" not in output))
    checks.append(
        ("no state-text false positive", "sensor.unrelated_note" not in output)
    )
    checks.append(("HACS entities are informational", result.hacs >= 2))
    checks.append(("real references are confirmed", result.confirmed >= 4))
    checks.append(("HACS lines are labelled", "[HACS]" in output))
    checks.append(
        ("HomeKit bridge referencing BTicino is detected", "HomeKit config entry" in output)
    )
    checks.append(
        ("legacy dashboard reference is detected", "button.condominium_gate" in output)
    )

    bticino_entity = ENTITY_REGISTRY["data"]["entities"][0]
    hacs_entity = ENTITY_REGISTRY["data"]["entities"][1]
    hacs_restore = {"state": {"entity_id": f"update.{DOMAIN}_update", "state": "on"}}
    video_restore = RESTORE_STATE["data"][2]

    checks.append(("cleaner matches BTicino entity", contains_bticino_reference(bticino_entity)))
    checks.append(("cleaner ignores HACS entity", not contains_bticino_reference(hacs_entity)))
    checks.append(("cleaner ignores HACS restore state", not contains_bticino_reference(hacs_restore)))
    checks.append(("cleaner ignores unrelated entity", not contains_bticino_reference(video_restore)))
    # A non-HACS entity with an update.* entity_id must not be misclassified.
    non_hacs_update = {
        "entity_id": f"update.{DOMAIN}_firmware",
        "platform": DOMAIN,
    }
    checks.append(("non-HACS update entity is not HACS", not is_hacs_managed(non_hacs_update)))

    checks.append(("is_bticino_entity accepts BTicino", is_bticino_entity(bticino_entity, {"bt1"})))
    checks.append(("is_bticino_entity rejects HACS", not is_bticino_entity(hacs_entity, {"bt1"})))

    ok = True
    for label, passed in checks:
        print(f"{'OK' if passed else 'FAIL'}: {label}")
        ok = ok and passed

    if ok:
        print(f"\nAll {len(checks)} reference-scan assertions passed.")
        return 0

    print("\nReference-scan self-test failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
