"""Console report rendering for health checks."""

from __future__ import annotations

from .result import CheckStatus, HealthCheckResult


EXIT_CODE_PASS = 0
EXIT_CODE_WARNING = 2
EXIT_CODE_FAIL = 1


def _status_symbol(status: CheckStatus) -> str:
    """Return a readable status symbol."""
    if status == CheckStatus.PASS:
        return "OK"

    if status == CheckStatus.WARNING:
        return "WARNING"

    return "FAIL"


def render_console_report(results: list[HealthCheckResult]) -> int:
    """Render a console health check report and return the process exit code."""
    print("=" * 72)
    print("BTicino CLASSE100X Home Assistant Health Check")
    print("=" * 72)
    print()

    for result in results:
        print(result.name)
        print("-" * len(result.name))
        print(f"Status: {_status_symbol(result.status)}")
        print(f"Summary: {result.summary}")

        if result.details:
            print()
            print("Details:")
            for detail in result.details:
                print(f"  - {detail}")

        if result.warnings:
            print()
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")

        print()

    overall_status = _overall_status(results)

    print("-" * 72)
    print(f"OVERALL STATUS: {_status_symbol(overall_status)}")
    print("-" * 72)

    if overall_status == CheckStatus.FAIL:
        return EXIT_CODE_FAIL

    if overall_status == CheckStatus.WARNING:
        return EXIT_CODE_WARNING

    return EXIT_CODE_PASS


def render_markdown_report(results: list[HealthCheckResult]) -> int:
    """Render a Markdown health check report and return the process exit code."""
    print("# BTicino CLASSE100X Home Assistant Health Check")
    print()

    for result in results:
        print(f"## {result.name}")
        print()
        print(f"**Status:** `{result.status}`")
        print()
        print(result.summary)
        print()

        if result.details:
            print("### Details")
            for detail in result.details:
                print(f"- {detail}")
            print()

        if result.warnings:
            print("### Warnings")
            for warning in result.warnings:
                print(f"- {warning}")
            print()

        if result.errors:
            print("### Errors")
            for error in result.errors:
                print(f"- {error}")
            print()

    overall_status = _overall_status(results)
    print(f"## Overall status: `{overall_status}`")

    if overall_status == CheckStatus.FAIL:
        return EXIT_CODE_FAIL

    if overall_status == CheckStatus.WARNING:
        return EXIT_CODE_WARNING

    return EXIT_CODE_PASS


def _overall_status(results: list[HealthCheckResult]) -> CheckStatus:
    """Return the overall health check status."""
    if any(result.status == CheckStatus.FAIL for result in results):
        return CheckStatus.FAIL

    if any(result.status == CheckStatus.WARNING for result in results):
        return CheckStatus.WARNING

    return CheckStatus.PASS