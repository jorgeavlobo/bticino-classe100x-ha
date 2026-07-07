"""Console report rendering for health checks."""

from __future__ import annotations

from .result import HealthCheckResult


def render_report(results: list[HealthCheckResult]) -> int:
    """Render a health check report and return the process exit code."""
    print("=" * 72)
    print("BTicino CLASSE100X Home Assistant Health Check")
    print("=" * 72)
    print()

    has_errors = False

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.name}: {status}")

        for detail in result.details:
            print(f"  - {detail}")

        for warning in result.warnings:
            print(f"  WARNING: {warning}")

        for error in result.errors:
            print(f"  ERROR: {error}")
            has_errors = True

        print()

    print("-" * 72)
    print("OVERALL STATUS:", "FAIL" if has_errors else "PASS")
    print("-" * 72)

    return 1 if has_errors else 0