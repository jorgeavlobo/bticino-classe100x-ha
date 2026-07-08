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
            # A HomeKit bridge that exposes ONLY a HACS management entity (whose
            # id embeds the integration name) must not be confirmed or cleaned:
            # HACS entities are informational only.
            {
                "entry_id": "hk_hacs_only",
                "domain": "homekit",
                "data": {
                    "entities": [f"switch.{DOMAIN}_pre_release"],
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
            # A legacy entry left by the removed ``bticino_classe100x_buttons``
            # platform: it carries no BTicino platform, unique_id prefix or live
            # config entry, but its entity_id is a known legacy id, so the clean
            # tools remove it and the scan must confirm it too.
            {
                "entity_id": "button.condominium_gate",
                "unique_id": "old_gate_button",
                "platform": "removed_buttons_platform",
                "config_entry_id": "gone",
            },
            # An unrelated entity from another integration whose object id merely
            # embeds the integration name as a substring (not the
            # ``bticino_classe100x_`` object-id prefix, and on a foreign
            # platform): structural matching must not flag it, so the cleaner
            # keeps it and the scan does not report it.
            {
                "entity_id": "sensor.foreign_bticino_classe100x_note",
                "unique_id": "foreign_note",
                "platform": "other_intercom",
                "config_entry_id": "oth1",
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
        # Unrelated entity whose STATE text is exactly a legacy entity id (e.g. a
        # history/text sensor mirroring another entity): still must not match,
        # because matching is on the entity_id, never the state text.
        {
            "state": {
                "entity_id": "sensor.last_triggered",
                "state": "automation.condominium_gate_opening",
            }
        },
        # An unrelated entity whose object id merely CONTAINS the token as a
        # substring (``my_bticino_classe100x``, not the ``bticino_classe100x_``
        # object-id prefix): matching is on the prefix, so this must not match.
        {
            "state": {
                "entity_id": "sensor.my_bticino_classe100x",
                "state": "x",
            }
        },
        # A legacy room-prefixed entity id (``<room>_bticino_classe100x_<key>``)
        # from the old naming strategy: matched via the legacy object-id
        # fragments, so the cleaner removes it and the scan confirms it.
        {
            "state": {
                "entity_id": "button.entrance_hall_bticino_classe100x_condominium_gate",
                "state": "idle",
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
# A single compact dashboard line referencing both a HACS entity and a real
# BTicino entity must be counted as a confirmed reference, not downgraded to
# HACS. ``uptime`` appears only here so it can be asserted precisely.
MIXED_DASHBOARD = json.dumps(
    {
        "cards": [
            {"entity": f"update.{DOMAIN}_update"},
            {"entity": f"sensor.{DOMAIN}_uptime"},
        ]
    }
)
# HACS's own bookkeeping records the integration by name. Any match here is
# informational (owned by HACS), never a confirmed reference the clean tools
# would act on. ``hacs_bookkeeping_marker`` appears only here so it can be
# asserted precisely.
HACS_DATA = json.dumps(
    {
        "repositories": {
            "1": {
                "full_name": "jorgeavlobo/bticino-classe100x-ha",
                "domain": DOMAIN,
                "note": "hacs_bookkeeping_marker",
            }
        }
    }
)
# A dashboard referencing a real entity whose id merely starts with a HACS id
# but is not exactly it (a suffixed ``..._update_2`` Home Assistant may create).
# Stripping HACS ids as whole tokens must leave this intact, so it is confirmed.
SUFFIXED_DASHBOARD = json.dumps(
    {"cards": [{"entity": f"update.{DOMAIN}_update_2"}]}
)


def _write_fixture(base: Path) -> None:
    storage = base / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "core.config_entries").write_text(json.dumps(CONFIG_ENTRIES), "utf-8")
    (storage / "core.entity_registry").write_text(json.dumps(ENTITY_REGISTRY), "utf-8")
    (storage / "core.device_registry").write_text(json.dumps(DEVICE_REGISTRY), "utf-8")
    (storage / "core.restore_state").write_text(json.dumps(RESTORE_STATE), "utf-8")
    (storage / "lovelace").write_text(LOVELACE, "utf-8")
    (storage / "lovelace.legacy").write_text(LEGACY_DASHBOARD, "utf-8")
    (storage / "lovelace.mixed").write_text(MIXED_DASHBOARD, "utf-8")
    (storage / "hacs.data").write_text(HACS_DATA, "utf-8")
    (storage / "lovelace.suffixed").write_text(SUFFIXED_DASHBOARD, "utf-8")


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


def _scan_hacs_only_dashboard() -> object:
    """Scan a storage dir whose only match is a HACS entity in a dashboard.

    There is no ``core.entity_registry``/``core.restore_state`` to discover the
    HACS entities from, so the text pass must rely on the known static HACS ids
    to classify the line as informational rather than confirmed.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = Path(temp_dir) / ".storage"
        storage.mkdir(parents=True, exist_ok=True)
        (storage / "lovelace").write_text(
            json.dumps({"cards": [{"entity": f"switch.{DOMAIN}_pre_release"}]}),
            "utf-8",
        )
        buffer = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buffer
        try:
            return find_references(ToolOptions(config_path=Path(temp_dir)))
        finally:
            sys.stdout = stdout


# Corrupted / schema-drifted storage: non-dict entries, a non-list bucket, and a
# storage file whose top-level JSON is not an object. The scan must degrade
# gracefully (never raise), still confirm the well-formed BTicino references, and
# count the unparsable-shape file as unreadable (an incomplete scan).
MALFORMED_CONFIG_ENTRIES = {
    "data": {
        "entries": [
            "not-a-dict",
            {"entry_id": "bt1", "domain": DOMAIN, "data": {"host": HOST}},
        ]
    }
}
MALFORMED_ENTITY_REGISTRY = {
    "data": {
        "entities": [
            42,
            {
                "entity_id": f"sensor.{DOMAIN}_health_status",
                "unique_id": f"{DOMAIN}_health_status",
                "platform": DOMAIN,
            },
        ],
        # A non-list bucket must be skipped, not iterated.
        "deleted_entities": "corrupt",
    }
}
MALFORMED_DEVICE_REGISTRY = {
    "data": {"devices": ["x", {"id": "d1", "identifiers": [[DOMAIN, HOST]]}]}
}
MALFORMED_RESTORE_STATE = {
    "data": [
        "str",
        {"state": {"entity_id": f"sensor.{DOMAIN}_uptime", "state": "1"}},
    ]
}


def _write_malformed_fixture(base: Path) -> None:
    storage = base / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "core.config_entries").write_text(
        json.dumps(MALFORMED_CONFIG_ENTRIES), "utf-8"
    )
    (storage / "core.entity_registry").write_text(
        json.dumps(MALFORMED_ENTITY_REGISTRY), "utf-8"
    )
    # Top-level JSON is a list, not an object: must be treated as unreadable.
    (storage / "core.device_registry").write_text(
        json.dumps([MALFORMED_DEVICE_REGISTRY]), "utf-8"
    )
    (storage / "core.restore_state").write_text(
        json.dumps(MALFORMED_RESTORE_STATE), "utf-8"
    )


def _scan_malformed() -> object:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        _write_malformed_fixture(base)
        buffer = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buffer
        try:
            return find_references(ToolOptions(config_path=base))
        finally:
            sys.stdout = stdout


def main() -> int:
    """Run every assertion and report the outcome."""
    checks: list[tuple[str, bool]] = []

    result, output = _scan()
    checks.append(("scan completed", result.storage_found and result.unreadable == 0))
    checks.append(("no video_intercom false positive", "video_intercom" not in output))
    checks.append(
        ("no state-text false positive", "sensor.unrelated_note" not in output)
    )
    checks.append(
        ("no legacy-id-in-state false positive", "sensor.last_triggered" not in output)
    )
    checks.append(("HACS entities are informational", result.hacs >= 2))
    checks.append(("real references are confirmed", result.confirmed >= 4))
    checks.append(("HACS lines are labelled", "[HACS]" in output))
    checks.append(
        ("HomeKit bridge referencing BTicino is detected", "HomeKit config entry" in output)
    )
    # A HomeKit bridge that exposes only a HACS-managed entity must not be
    # reported as a confirmed BTicino reference (HACS ids are stripped first).
    checks.append(
        ("HACS-only HomeKit bridge is not confirmed", "hk_hacs_only" not in output)
    )
    # A dashboard referencing a real entity whose id only starts with a HACS id
    # (suffixed ``..._update_2``) must be confirmed: HACS ids are stripped as
    # whole tokens, so the suffixed id is not neutralized.
    suffixed_lines = [
        line
        for line in output.splitlines()
        if f"update.{DOMAIN}_update_2" in line
    ]
    checks.append(
        (
            "suffixed real entity in dashboard is confirmed",
            bool(suffixed_lines)
            and all(not line.startswith("[HACS]") for line in suffixed_lines),
        )
    )
    checks.append(
        ("legacy dashboard reference is detected", "button.condominium_gate" in output)
    )
    # A legacy registry entry (no BTicino platform/unique_id/config entry, only a
    # legacy entity_id) must be confirmed, matching what clean_entity_registry
    # removes. Its unique_id appears only on the registry line.
    checks.append(
        ("legacy registry entry is confirmed", "old_gate_button" in output)
    )
    # A restore-state entity whose object id merely contains the token as a
    # substring must not be reported (matching is on the object-id prefix).
    checks.append(
        (
            "no object-id-substring false positive",
            "sensor.my_bticino_classe100x" not in output,
        )
    )
    # A legacy room-prefixed restore entity must be confirmed (matched via the
    # legacy object-id fragments), mirroring what clean_restore_state removes.
    checks.append(
        (
            "legacy room-prefixed restore entry is confirmed",
            "entrance_hall_bticino_classe100x_condominium_gate" in output,
        )
    )
    # A registry entity on a foreign platform whose object id only embeds the
    # integration name as a substring must not be reported (structural match).
    checks.append(
        (
            "no registry object-id-substring false positive",
            "sensor.foreign_bticino_classe100x_note" not in output,
        )
    )
    # HACS bookkeeping files are informational: their lines must be labelled
    # [HACS] and never counted as confirmed references.
    hacs_data_lines = [
        line for line in output.splitlines() if "hacs_bookkeeping_marker" in line
    ]
    checks.append(
        (
            "HACS bookkeeping file is informational",
            bool(hacs_data_lines)
            and all(line.startswith("[HACS]") for line in hacs_data_lines),
        )
    )
    # A line that mixes a HACS entity and a real BTicino entity must be confirmed
    # (not downgraded to informational). "uptime" appears only on that line.
    uptime_lines = [
        line for line in output.splitlines() if f"sensor.{DOMAIN}_uptime" in line
    ]
    checks.append(
        (
            "mixed HACS+real dashboard line is confirmed",
            bool(uptime_lines)
            and all(not line.startswith("[HACS]") for line in uptime_lines),
        )
    )

    bticino_entity = ENTITY_REGISTRY["data"]["entities"][0]
    hacs_entity = ENTITY_REGISTRY["data"]["entities"][1]
    hacs_restore = {"state": {"entity_id": f"update.{DOMAIN}_update", "state": "on"}}
    video_restore = RESTORE_STATE["data"][2]

    legacy_entity = ENTITY_REGISTRY["data"]["entities"][4]
    foreign_entity = ENTITY_REGISTRY["data"]["entities"][5]
    hacs_only_homekit = CONFIG_ENTRIES["data"]["entries"][3]
    real_homekit = CONFIG_ENTRIES["data"]["entries"][2]
    legacy_id_in_state = RESTORE_STATE["data"][4]
    substring_restore = RESTORE_STATE["data"][5]
    room_prefixed_restore = RESTORE_STATE["data"][6]

    checks.append(("cleaner matches BTicino entity", contains_bticino_reference(bticino_entity)))
    checks.append(("cleaner matches legacy registry entry", contains_bticino_reference(legacy_entity)))
    checks.append(
        (
            "cleaner ignores foreign object-id-substring entity",
            not contains_bticino_reference(foreign_entity),
        )
    )
    checks.append(
        (
            "cleaner matches real HomeKit bridge",
            contains_bticino_reference(real_homekit),
        )
    )
    checks.append(
        (
            "cleaner ignores HACS-only HomeKit bridge",
            not contains_bticino_reference(hacs_only_homekit),
        )
    )
    # A HomeKit bridge exposing a real entity whose id only starts with a HACS
    # id (suffixed ``..._update_2``) must still be matched by the cleaner.
    suffixed_homekit = {
        "entry_id": "hk_suffixed",
        "domain": "homekit",
        "data": {"entities": [f"update.{DOMAIN}_update_2"]},
    }
    checks.append(
        (
            "cleaner matches HomeKit bridge with suffixed real entity",
            contains_bticino_reference(suffixed_homekit),
        )
    )
    checks.append(("cleaner ignores HACS entity", not contains_bticino_reference(hacs_entity)))
    checks.append(("cleaner ignores HACS restore state", not contains_bticino_reference(hacs_restore)))
    checks.append(("cleaner ignores unrelated entity", not contains_bticino_reference(video_restore)))
    # A restore entry whose free-form state text equals a legacy id must be kept:
    # matching is on the carried entity_id, never the state text.
    checks.append(
        (
            "cleaner ignores legacy-id-in-state restore",
            not contains_bticino_reference(legacy_id_in_state),
        )
    )
    # A restore entry whose object id merely contains the token as a substring
    # must be kept (matching is on the object-id prefix).
    checks.append(
        (
            "cleaner ignores object-id-substring restore",
            not contains_bticino_reference(substring_restore),
        )
    )
    # A legacy room-prefixed restore entry must be removed by the cleaner.
    checks.append(
        (
            "cleaner matches legacy room-prefixed restore",
            contains_bticino_reference(room_prefixed_restore),
        )
    )
    # A non-HACS entity with an update.* entity_id must not be misclassified.
    non_hacs_update = {
        "entity_id": f"update.{DOMAIN}_firmware",
        "platform": DOMAIN,
    }
    checks.append(("non-HACS update entity is not HACS", not is_hacs_managed(non_hacs_update)))
    # A restore-state entry whose id merely starts with the HACS id but is not
    # exactly it (e.g. a suffixed ``..._update_2``) must NOT be treated as HACS:
    # matching is by exact id, not prefix. It is a genuine BTicino entity.
    suffixed_update = {
        "state": {"entity_id": f"update.{DOMAIN}_update_2", "state": "on"}
    }
    checks.append(
        ("suffixed update entity is not HACS", not is_hacs_managed(suffixed_update))
    )
    checks.append(
        (
            "suffixed update entity is a BTicino reference",
            contains_bticino_reference(suffixed_update),
        )
    )

    checks.append(("is_bticino_entity accepts BTicino", is_bticino_entity(bticino_entity, {"bt1"})))
    checks.append(("is_bticino_entity rejects HACS", not is_bticino_entity(hacs_entity, {"bt1"})))

    # Corrupted / schema-drifted storage must degrade gracefully: the scan runs
    # to completion (no exception), still confirms the well-formed references
    # (one per config/entity/restore file = 3), and flags the file whose
    # top-level JSON is not an object as unreadable.
    try:
        malformed = _scan_malformed()
        malformed_ok = (
            malformed.storage_found
            and malformed.confirmed >= 3
            and malformed.unreadable >= 1
        )
    except Exception:  # noqa: BLE001 - any raise here is the failure under test
        malformed_ok = False
    checks.append(("malformed storage degrades gracefully", malformed_ok))

    # A dashboard that references only a HACS entity, with no registry files to
    # discover it from, must be informational (not confirmed) via the known
    # static HACS ids, so the exit code is not flipped to 1.
    hacs_only = _scan_hacs_only_dashboard()
    checks.append(
        (
            "HACS-only dashboard without registry is informational",
            hacs_only.storage_found
            and hacs_only.confirmed == 0
            and hacs_only.hacs >= 1,
        )
    )

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
