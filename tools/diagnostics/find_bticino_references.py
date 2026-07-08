"""Find BTicino CLASSE100X references in Home Assistant storage files."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import NamedTuple

# Insert the tools directory ahead of this script's own directory so the shared
# ``tools/shared`` package takes precedence over the local ``diagnostics/shared``
# package (which is used by the health check tool).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.cli import ToolOptions, build_parser, get_logger, parse_options
from shared.paths import storage_path


SEARCH_TERMS: tuple[str, ...] = (
    "bticino",
    "bticino_classe100x",
    "condominium",
    "pedestrian",
)


class ScanResult(NamedTuple):
    """Outcome of scanning the storage directory.

    ``storage_found`` is ``False`` when the storage path does not exist,
    ``matches`` is the number of matching lines, and ``unreadable`` counts the
    storage files that could not be read (so the scan is incomplete and cannot
    certify that no references remain).
    """

    storage_found: bool
    matches: int
    unreadable: int


def find_references(options: ToolOptions) -> ScanResult:
    """Print lines containing BTicino-related search terms.

    Returns a :class:`ScanResult` describing whether the storage was found, how
    many matching lines were printed, and how many files could not be read.
    """
    log = get_logger()
    storage = storage_path(options.config_path)

    if not storage.is_dir():
        log.warning("Storage path not found: %s", storage)
        return ScanResult(storage_found=False, matches=0, unreadable=0)

    matches = 0
    unreadable = 0

    for path in sorted(storage.iterdir()):
        if not path.is_file():
            continue

        # Skip the timestamped backups created by the clean tools so a finished
        # cleanup is not reported as still containing references.
        if ".backup_" in path.name:
            log.debug("Skipping backup file: %s", path)
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            # A file that cannot be read leaves the scan incomplete: it may still
            # contain references, so surface it rather than silently passing.
            log.warning("Could not read %s: %s", path, exc)
            unreadable += 1
            continue

        log.debug("Scanning %s", path)

        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(term in lowered for term in SEARCH_TERMS):
                matches += 1
                print(f"{path}:{index}: {line}")

    log.info("Found %d matching line(s) in %s", matches, storage)
    if unreadable:
        log.warning(
            "%d file(s) could not be read; the scan is incomplete", unreadable
        )

    return ScanResult(storage_found=True, matches=matches, unreadable=unreadable)


def main() -> None:
    """Run the reference finder.

    Exit codes: ``0`` when the storage was scanned in full and no references
    remain, ``1`` when references were found, and ``2`` when the scan could not
    be completed (the storage path is missing, for example a misconfigured
    ``--config``, or one or more files could not be read), so the tool can be
    used in scripts and CI to confirm a cleanup succeeded.
    """
    parser = build_parser(
        "Find BTicino references in Home Assistant storage files",
        include_write_options=False,
    )
    result = find_references(parse_options(parser))

    if not result.storage_found or result.unreadable > 0:
        sys.exit(2)
    sys.exit(1 if result.matches > 0 else 0)


if __name__ == "__main__":
    main()
