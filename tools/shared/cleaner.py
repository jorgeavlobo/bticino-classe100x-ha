"""Safe cleanup routine shared by the clean tools."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

from shared.backup import create_backup
from shared.cli import ToolOptions, confirm, get_logger
from shared.jsonfile import read_json, write_json

# A mutator reads the decoded storage file, removes the BTicino entries in place
# and returns a mapping of ``{label: removed_count}`` for reporting.
Mutator = Callable[[dict], dict[str, int]]


def run_cleanup(options: ToolOptions, path: Path, mutate: Mutator) -> bool:
    """Apply a cleanup to a storage file, backing up and confirming first.

    The file is read, ``mutate`` removes the matching entries, and the result is
    only written back when this is not a dry run, the user confirms, and (unless
    ``--no-backup``) a backup has been created.

    Returns ``True`` when the outcome is expected (updated, nothing to do, dry
    run, or a deliberate skip) and ``False`` only when the operation could not be
    completed (read, backup or write failure), so callers can set the exit code.
    """
    log = get_logger()

    if not path.exists():
        log.warning("Not found, skipping: %s", path)
        return True

    try:
        data = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        log.error("Could not read %s: %s", path, exc)
        return False

    try:
        removed = mutate(data)
    except Exception as exc:
        # Defensive boundary: a storage file with an unexpected schema should
        # produce a clean error and a non-zero exit code, not a traceback.
        log.error("Could not process %s: %s", path.name, exc)
        return False

    for label, count in removed.items():
        log.info("  %s: %d", label, count)

    total = sum(removed.values())
    if total == 0:
        log.info("Nothing to remove in %s", path.name)
        return True

    if options.dry_run:
        log.info(
            "Dry run: %s left unchanged (%d entry/entries would be removed)",
            path.name,
            total,
        )
        return True

    if not confirm(
        f"Remove {total} entry/entries from {path.name}?", options.assume_yes
    ):
        log.info("Skipped %s", path.name)
        return True

    if options.backup:
        try:
            backup_path = create_backup(path)
        except OSError as exc:
            log.error("Could not back up %s: %s; aborting", path.name, exc)
            return False

        if backup_path is None:
            log.error("Could not back up %s (file missing); aborting", path.name)
            return False

        log.info("Backup created: %s", backup_path)
    else:
        log.warning("Skipping backup for %s (--no-backup)", path.name)

    try:
        write_json(path, data)
    except OSError as exc:
        log.error("Could not write %s: %s", path, exc)
        return False

    log.info("Updated %s", path.name)
    return True
