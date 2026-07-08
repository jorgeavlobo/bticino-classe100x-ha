"""Find BTicino CLASSE100X references in Home Assistant storage files."""

from __future__ import annotations

from pathlib import Path
import sys

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


def find_references(options: ToolOptions) -> int:
    """Print lines containing BTicino-related search terms.

    Returns the number of matching lines found, or ``-1`` when the storage
    path does not exist so callers can tell a misconfigured ``--config`` apart
    from a genuinely clean scan.
    """
    log = get_logger()
    storage = storage_path(options.config_path)

    if not storage.is_dir():
        log.warning("Storage path not found: %s", storage)
        return -1

    matches = 0

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
        except (OSError, UnicodeDecodeError):
            log.debug("Skipping unreadable file: %s", path)
            continue

        log.debug("Scanning %s", path)

        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(term in lowered for term in SEARCH_TERMS):
                matches += 1
                print(f"{path}:{index}: {line}")

    log.info("Found %d matching line(s) in %s", matches, storage)
    return matches


def main() -> None:
    """Run the reference finder.

    Exit codes: ``0`` when the storage was scanned and no references remain,
    ``1`` when references were found, and ``2`` when the storage path is
    missing (for example a misconfigured ``--config``), so the tool can be used
    in scripts and CI to confirm a cleanup succeeded.
    """
    parser = build_parser(
        "Find BTicino references in Home Assistant storage files",
        include_write_options=False,
    )
    matches = find_references(parse_options(parser))

    if matches < 0:
        sys.exit(2)
    sys.exit(1 if matches > 0 else 0)


if __name__ == "__main__":
    main()
