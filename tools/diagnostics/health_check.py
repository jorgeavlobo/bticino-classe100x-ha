"""BTicino CLASSE100X Home Assistant health check tool."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
TOOLS_ROOT = CURRENT_FILE.parents[1]

sys.path.insert(0, str(TOOLS_ROOT))

from diagnostics.checks.entity_registry import check_entity_registry
from diagnostics.shared.report import render_report


def main() -> int:
    """Run the BTicino CLASSE100X health check."""
    parser = argparse.ArgumentParser(
        description="Run BTicino CLASSE100X Home Assistant health checks."
    )
    parser.add_argument(
        "--config",
        default="/config",
        help="Home Assistant config directory. Defaults to /config.",
    )

    args = parser.parse_args()
    config_path = Path(args.config)

    results = [
        check_entity_registry(config_path),
    ]

    return render_report(results)


if __name__ == "__main__":
    raise SystemExit(main())