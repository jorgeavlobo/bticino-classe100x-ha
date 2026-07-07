"""BTicino CLASSE100X Home Assistant health check tool."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
TOOLS_ROOT = CURRENT_FILE.parents[1]

sys.path.insert(0, str(TOOLS_ROOT))

from diagnostics.checks.config_entries import ConfigEntriesCheck
from diagnostics.checks.device_registry import DeviceRegistryCheck
from diagnostics.checks.entity_registry import EntityRegistryCheck
from diagnostics.checks.manifest import ManifestCheck
from diagnostics.checks.restore_state import RestoreStateCheck
from diagnostics.checks.translations import TranslationsCheck
from diagnostics.checks.yaml_config import YamlConfigCheck
from diagnostics.shared.report import render_console_report, render_markdown_report


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
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Render the health check report as Markdown.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Reserved for future automatic fixes. Currently not implemented.",
    )

    args = parser.parse_args()

    if args.fix:
        print("Automatic fixes are not implemented yet.")
        return 1

    config_path = Path(args.config)

    checks = [
        EntityRegistryCheck(),
        RestoreStateCheck(),
        ConfigEntriesCheck(),
        DeviceRegistryCheck(),
        ManifestCheck(),
        TranslationsCheck(),
        YamlConfigCheck(),
    ]

    results = [
        check.run(config_path)
        for check in checks
    ]

    if args.markdown:
        return render_markdown_report(results)

    return render_console_report(results)


if __name__ == "__main__":
    raise SystemExit(main())