"""BTicino CLASSE100X Home Assistant health check tool."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from time import perf_counter

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
from diagnostics.shared.check import HealthCheck
from diagnostics.shared.report import (
    render_console_report,
    render_github_report,
    render_json_report,
    render_markdown_report,
)


def _available_checks() -> dict[str, HealthCheck]:
    """Return all available health checks."""
    return {
        "entity_registry": EntityRegistryCheck(),
        "restore_state": RestoreStateCheck(),
        "config_entries": ConfigEntriesCheck(),
        "device_registry": DeviceRegistryCheck(),
        "manifest": ManifestCheck(),
        "translations": TranslationsCheck(),
        "yaml": YamlConfigCheck(),
    }


def main() -> int:
    """Run the BTicino CLASSE100X health check."""
    parser = argparse.ArgumentParser(
        description="Run BTicino CLASSE100X Home Assistant health checks."
    )
    parser.add_argument(
        "checks",
        nargs="*",
        help="Optional check names to run. Use --list to see available checks.",
    )
    parser.add_argument(
        "--config",
        default="/config",
        help="Home Assistant config directory. Defaults to /config.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available health checks.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Render the health check report as JSON.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Render the health check report as Markdown.",
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="Render a GitHub issue friendly Markdown report.",
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Measure and display how long each check takes.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Reserved for future automatic fixes. Currently not implemented.",
    )

    args = parser.parse_args()
    available_checks = _available_checks()

    if args.list:
        print("Available checks:")
        for check_key, check in available_checks.items():
            print(f"  {check_key}: {check.name}")
        return 0

    if args.fix:
        print("Automatic fixes are not implemented yet.")
        return 1

    selected_checks = _select_checks(
        available_checks=available_checks,
        requested_checks=args.checks,
    )

    if selected_checks is None:
        return 1

    config_path = Path(args.config)

    results = [
        _run_check(
            check=check,
            config_path=config_path,
            measure_performance=args.performance,
        )
        for check in selected_checks
    ]

    if args.json:
        return render_json_report(results)

    if args.github:
        return render_github_report(results)

    if args.markdown:
        return render_markdown_report(results)

    return render_console_report(results)


def _select_checks(
    available_checks: dict[str, HealthCheck],
    requested_checks: list[str],
) -> list[HealthCheck] | None:
    """Return the checks requested by the user."""
    if not requested_checks:
        return list(available_checks.values())

    invalid_checks = [
        check_name
        for check_name in requested_checks
        if check_name not in available_checks
    ]

    if invalid_checks:
        print("Unknown check name(s):")
        for check_name in invalid_checks:
            print(f"  {check_name}")

        print()
        print("Use --list to see available checks.")
        return None

    return [
        available_checks[check_name]
        for check_name in requested_checks
    ]


def _run_check(
    check: HealthCheck,
    config_path: Path,
    measure_performance: bool,
):
    """Run a single health check."""
    if not measure_performance:
        return check.run(config_path)

    start_time = perf_counter()
    result = check.run(config_path)
    end_time = perf_counter()

    result.duration_ms = (end_time - start_time) * 1000

    return result


if __name__ == "__main__":
    raise SystemExit(main())