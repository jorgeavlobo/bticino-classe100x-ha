"""Find BTicino CLASSE100X references in Home Assistant storage files.

References are identified by structural identifiers (the integration domain,
entity platform, entity_id/unique_id prefix, config-entry domain and device
identifiers) rather than by generic words, so entities that merely mention a
word such as "condominium" are no longer reported. HACS management entities
(``update``/``switch`` created by HACS) are reported separately as
informational and never count as BTicino references.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, NamedTuple

# Insert the tools directory ahead of this script's own directory so the shared
# ``tools/shared`` package takes precedence over the local ``diagnostics/shared``
# package for the bare ``shared`` name, while ``diagnostics.shared`` stays
# importable by its fully qualified name.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagnostics.shared.entities import (
    DOMAIN,
    bticino_config_entry_ids,
    is_bticino_entity,
    is_hacs_entity,
    mentions_bticino,
)
from shared.cli import ToolOptions, build_parser, get_logger, parse_options
from shared.hacs import HACS_ENTITY_IDS, strip_hacs_entity_ids
from shared.jsonfile import read_json
from shared.matching import (
    LEGACY_ENTITY_IDS,
    contains_bticino_reference,
    is_bticino_entity_id,
    is_hacs_managed,
)
from shared.paths import storage_path

# The structural token used for the free-form text scan. Legacy ids such as
# ``entrance_hall_bticino_classe100x`` contain it, so a single token is enough.
STRUCTURAL_TOKEN = DOMAIN

# Files parsed structurally; they are skipped by the text scan.
STRUCTURED_FILES = (
    "core.config_entries",
    "core.entity_registry",
    "core.device_registry",
    "core.restore_state",
)


class ScanResult(NamedTuple):
    """Outcome of scanning the storage directory.

    ``storage_found`` is ``False`` when the storage path does not exist,
    ``confirmed`` counts confirmed BTicino references, ``hacs`` counts
    HACS-managed entities that mention the integration (informational only), and
    ``unreadable`` counts files that could not be read (an incomplete scan).
    """

    storage_found: bool
    confirmed: int
    hacs: int
    unreadable: int


def _read(path: Path) -> dict[str, Any] | None:
    """Read a JSON storage file, returning None when it cannot be read.

    Home Assistant storage files are always JSON objects; a parsed value that is
    not a dict is treated as unreadable (corrupt) so the caller records an
    incomplete scan instead of crashing on a later attribute access.
    """
    try:
        data = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _records(container: Any, *keys: str) -> list[Any]:
    """Return the list nested under ``keys``, degrading gracefully.

    A corrupted or schema-drifted storage file may not have the expected shape.
    Any non-dict node along the path, or a final value that is not a list,
    yields an empty list instead of raising, so the scan never aborts on a
    single malformed file.
    """
    node: Any = container
    for key in keys:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    return node if isinstance(node, list) else []


def _identifiers_reference_bticino(identifiers: Any) -> bool:
    """Return true if a device's identifiers reference the integration."""
    if not isinstance(identifiers, list):
        return False
    return any(
        isinstance(identifier, (list, tuple))
        and identifier
        and identifier[0] == DOMAIN
        for identifier in identifiers
    )


def _line_references_bticino(line: str) -> bool:
    """Return true if a text line references BTicino by token or legacy id."""
    return STRUCTURAL_TOKEN in line.lower() or any(
        legacy_id in line for legacy_id in LEGACY_ENTITY_IDS
    )


def _restore_state_entity_id(entry: Any) -> Any:
    """Return the entity_id carried by a restore-state entry, if any."""
    if isinstance(entry, dict):
        state = entry.get("state")
        if isinstance(state, dict):
            return state.get("entity_id")
    return None


def find_references(options: ToolOptions) -> ScanResult:
    """Report BTicino references found in the Home Assistant storage files."""
    log = get_logger()
    storage = storage_path(options.config_path)

    if not storage.is_dir():
        log.warning("Storage path not found: %s", storage)
        return ScanResult(storage_found=False, confirmed=0, hacs=0, unreadable=0)

    confirmed = 0
    hacs = 0
    unreadable = 0
    hacs_entity_ids: set[str] = set()

    # --- Structural pass over the registries --------------------------------

    config_entry_ids: set[str] = set()
    config_entries_path = storage / "core.config_entries"
    if config_entries_path.is_file():
        config_entries = _read(config_entries_path)
        if config_entries is None:
            log.warning("Could not read %s", config_entries_path)
            unreadable += 1
        else:
            config_entry_ids = set(bticino_config_entry_ids(config_entries))
            for entry in _records(config_entries, "data", "entries"):
                if not isinstance(entry, dict):
                    continue
                domain = entry.get("domain")
                if domain == DOMAIN:
                    confirmed += 1
                    print(
                        f"{config_entries_path.name}: config entry "
                        f"{entry.get('entry_id')} (domain: {DOMAIN})"
                    )
                elif domain == "homekit" and contains_bticino_reference(entry):
                    # A HomeKit bridge that exposes BTicino entities is a BTicino
                    # reference too (clean_config_entries treats it as one).
                    confirmed += 1
                    print(
                        f"{config_entries_path.name}: HomeKit config entry "
                        f"{entry.get('entry_id')} references BTicino entities"
                    )

    entity_registry_path = storage / "core.entity_registry"
    if entity_registry_path.is_file():
        registry = _read(entity_registry_path)
        if registry is None:
            log.warning("Could not read %s", entity_registry_path)
            unreadable += 1
        else:
            for bucket in ("entities", "deleted_entities"):
                for entity in _records(registry, "data", bucket):
                    if not isinstance(entity, dict):
                        continue
                    entity_id = entity.get("entity_id")
                    if is_hacs_entity(entity) and mentions_bticino(entity):
                        hacs += 1
                        if isinstance(entity_id, str):
                            hacs_entity_ids.add(entity_id)
                        print(
                            f"[HACS] {entity_registry_path.name} ({bucket}): "
                            f"{entity_id} (unique_id: {entity.get('unique_id')})"
                        )
                    elif is_bticino_entity(entity, config_entry_ids) or (
                        contains_bticino_reference(entity)
                    ):
                        # The second clause mirrors clean_entity_registry, which
                        # uses the same predicate: for an entry carrying a
                        # ``platform`` it matches structurally on the identifiers
                        # (entity_id current/legacy forms, unique_id prefix or
                        # platform). It catches legacy entries (e.g. a
                        # ``button.condominium_gate`` left by the old
                        # ``bticino_classe100x_buttons`` platform) that no longer
                        # carry a current BTicino platform/unique_id or a live
                        # config entry, keeping the scan and the cleanup aligned.
                        confirmed += 1
                        print(
                            f"{entity_registry_path.name} ({bucket}): "
                            f"{entity_id} (unique_id: {entity.get('unique_id')})"
                        )

    device_registry_path = storage / "core.device_registry"
    if device_registry_path.is_file():
        devices = _read(device_registry_path)
        if devices is None:
            log.warning("Could not read %s", device_registry_path)
            unreadable += 1
        else:
            for bucket in ("devices", "deleted_devices"):
                for device in _records(devices, "data", bucket):
                    if not isinstance(device, dict):
                        continue
                    if _identifiers_reference_bticino(device.get("identifiers")):
                        confirmed += 1
                        print(
                            f"{device_registry_path.name} ({bucket}): device "
                            f"{device.get('id')} ({device.get('name')})"
                        )

    restore_state_path = storage / "core.restore_state"
    if restore_state_path.is_file():
        restore_state = _read(restore_state_path)
        if restore_state is None:
            log.warning("Could not read %s", restore_state_path)
            unreadable += 1
        else:
            for entry in _records(restore_state, "data"):
                # Match on the entry's entity_id, never its free-form state text,
                # so an unrelated entity whose state mentions a word like
                # "condominium" (or even the token) is not reported.
                entity_id = _restore_state_entity_id(entry)
                if not isinstance(entity_id, str):
                    continue

                if is_hacs_managed(entry):
                    hacs += 1
                    hacs_entity_ids.add(entity_id)
                    print(f"[HACS] {restore_state_path.name}: {entity_id}")
                elif is_bticino_entity_id(entity_id):
                    # Match the object-id prefix (or a legacy id), never a bare
                    # substring, so an unrelated ``sensor.my_bticino_classe100x``
                    # is not reported.
                    confirmed += 1
                    print(f"{restore_state_path.name}: {entity_id}")

    # --- Text pass over the remaining files ---------------------------------

    for path in sorted(storage.iterdir()):
        if not path.is_file() or path.name in STRUCTURED_FILES:
            continue

        # Skip the timestamped backups created by the clean tools so a finished
        # cleanup is not reported as still containing references.
        if ".backup_" in path.name:
            log.debug("Skipping backup file: %s", path)
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            log.warning("Could not read %s: %s", path, exc)
            unreadable += 1
            continue

        # HACS keeps its own bookkeeping (``hacs.data``, ``hacs.repositories``)
        # which records the integration by name. These are owned by HACS, not by
        # this integration, so any match is informational, never a confirmed
        # reference the clean tools would act on.
        hacs_file = path.name == "hacs" or path.name.startswith("hacs.")

        for index, line in enumerate(lines, start=1):
            # Match the integration token or an exact legacy entity id (the same
            # ids the clean tools remove), so a stale dashboard/script reference
            # is not missed.
            if not _line_references_bticino(line):
                continue

            if hacs_file:
                hacs += 1
                print(f"[HACS] {path.name}:{index}: {line.strip()}")
                continue

            # A single compact JSON line (Home Assistant writes .storage on one
            # line) can reference both a HACS entity and a real BTicino entity.
            # Remove the HACS entity ids first; only if no BTicino reference
            # remains is the line HACS-only, so a real reference is never
            # downgraded to informational. Both the known static HACS ids and
            # any discovered in the registries are stripped, so a line that
            # references only a HACS entity is informational even when the HACS
            # entities are absent from (or their registry files unreadable in)
            # this storage copy. Whole entity ids are stripped (never a bare
            # prefix), so a suffixed real entity such as
            # ``update.bticino_classe100x_update_2`` still counts as confirmed.
            remainder = strip_hacs_entity_ids(line, HACS_ENTITY_IDS | hacs_entity_ids)

            if _line_references_bticino(remainder):
                confirmed += 1
                print(f"{path.name}:{index}: {line.strip()}")
            else:
                hacs += 1
                print(f"[HACS] {path.name}:{index}: {line.strip()}")

    log.info(
        "Confirmed BTicino references: %d; HACS-managed entities: %d (in %s)",
        confirmed,
        hacs,
        storage,
    )
    if unreadable:
        log.warning(
            "%d files could not be read; the scan is incomplete", unreadable
        )

    return ScanResult(
        storage_found=True, confirmed=confirmed, hacs=hacs, unreadable=unreadable
    )


def main() -> None:
    """Run the reference finder.

    Exit codes: ``0`` when the storage was scanned in full and no confirmed
    references remain, ``1`` when confirmed references were found, and ``2`` when
    the scan could not be completed (missing storage path or unreadable files).
    HACS-managed entities are informational and never affect the exit code.
    """
    parser = build_parser(
        "Find BTicino references in Home Assistant storage files",
        include_write_options=False,
    )
    result = find_references(parse_options(parser))

    if not result.storage_found or result.unreadable > 0:
        sys.exit(2)
    sys.exit(1 if result.confirmed > 0 else 0)


if __name__ == "__main__":
    main()
