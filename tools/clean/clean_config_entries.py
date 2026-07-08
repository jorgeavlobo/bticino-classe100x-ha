"""Clean BTicino CLASSE100X config entries from Home Assistant."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.cleaner import run_cleanup
from shared.cli import ToolOptions, build_parser, parse_options
from shared.matching import contains_bticino_reference
from shared.paths import config_entries_path


def _is_bticino_entry(entry: dict) -> bool:
    """Return true for BTicino or BTicino-related HomeKit config entries."""
    return entry.get("domain") == "bticino_classe100x" or (
        entry.get("domain") == "homekit" and contains_bticino_reference(entry)
    )


def clean_config_entries(options: ToolOptions) -> None:
    """Remove BTicino and BTicino-related HomeKit config entries."""

    def mutate(config_entries: dict) -> dict[str, int]:
        data = config_entries.get("data", {})
        entries = data.get("entries", [])
        kept = [entry for entry in entries if not _is_bticino_entry(entry)]
        data["entries"] = kept

        return {"config entries": len(entries) - len(kept)}

    run_cleanup(options, config_entries_path(options.config_path), mutate)


def main() -> None:
    """Run the config entries cleanup tool."""
    parser = build_parser("Clean BTicino entries from core.config_entries")
    clean_config_entries(parse_options(parser))


if __name__ == "__main__":
    main()
