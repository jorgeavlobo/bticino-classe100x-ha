"""Clean BTicino CLASSE100X restore states from Home Assistant."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.cleaner import run_cleanup
from shared.cli import ToolOptions, build_parser, parse_options
from shared.matching import contains_bticino_reference
from shared.paths import restore_state_path


def clean_restore_state(options: ToolOptions) -> bool:
    """Remove BTicino-related entries from core.restore_state."""

    def mutate(restore_state: dict) -> dict[str, int]:
        entries = restore_state.get("data", [])
        kept = [entry for entry in entries if not contains_bticino_reference(entry)]
        restore_state["data"] = kept

        return {"restore state entries": len(entries) - len(kept)}

    return run_cleanup(options, restore_state_path(options.config_path), mutate)


def main() -> None:
    """Run the restore state cleanup tool."""
    parser = build_parser("Clean BTicino entries from core.restore_state")
    if not clean_restore_state(parse_options(parser)):
        sys.exit(1)


if __name__ == "__main__":
    main()
