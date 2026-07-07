"""Report rendering for health checks."""

from __future__ import annotations

import json
from typing import Any

from .result import CheckStatus, HealthCheckResult


EXIT_CODE_PASS = 0
EXIT_CODE_WARNING = 2
EXIT_CODE_FAIL = 1


def render_console_report(results: list[HealthCheckResult]) -> int:
    """Render a console health check report and return the process exit code."""
    print("=" * 72)
    print("BTicino CLASSE100X Home Assistant Health Check")
    print("=" * 72)
    print()

    for result in results:
        print(result.name)
        print("-" * len(result.name))
        print(f"Status: {_status_text(result.status)}")
        print(f"Summary: {result.summary}")

        if result.duration_ms is not None:
            print(f"Duration: {result.duration_ms:.2f} ms")

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
    print(f"OVERALL STATUS: {_status_text(overall_status)}")
    print("-" * 72)

    return _exit_code(overall_status)


def render_markdown_report(results: list[HealthCheckResult]) -> int:
    """Render a Markdown health check report and return the process exit code."""
    print("# BTicino CLASSE100X Home Assistant Health Check")
    print()

    for result in results:
        print(f"## {result.name}")
        print()
        print(f"**Status:** `{result.status.value}`")
        print()
        print(result.summary)
        print()

        if result.duration_ms is not None:
            print(f"**Duration:** `{result.duration_ms:.2f} ms`")
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
    print(f"## Overall status: `{overall_status.value}`")

    return _exit_code(overall_status)


def render_github_report(results: list[HealthCheckResult]) -> int:
    """Render a GitHub-friendly Markdown health check report."""
    print("## BTicino CLASSE100X Health Check")
    print()

    for result in results:
        symbol = _github_symbol(result.status)
        print(f"- {symbol} **{result.name}** — `{result.status.value}`")

        if result.duration_ms is not None:
            print(f"  - Duration: `{result.duration_ms:.2f} ms`")

        if result.summary:
            print(f"  - {result.summary}")

        for error in result.errors:
            print(f"  - Error: `{error}`")

        for warning in result.warnings:
            print(f"  - Warning: `{warning}`")

    overall_status = _overall_status(results)
    print()
    print(f"**Overall status:** `{overall_status.value}`")

    return _exit_code(overall_status)


def render_json_report(results: list[HealthCheckResult]) -> int:
    """Render a JSON health check report."""
    overall_status = _overall_status(results)

    payload: dict[str, Any] = {
        "overall_status": overall_status.value,
        "checks": [
            {
                "name": result.name,
                "status": result.status.value,
                "summary": result.summary,
                "details": result.details,
                "warnings": result.warnings,
                "errors": result.errors,
                "duration_ms": result.duration_ms,
            }
            for result in results
        ],
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return _exit_code(overall_status)


def _overall_status(results: list[HealthCheckResult]) -> CheckStatus:
    """Return the overall health check status."""
    if any(result.status == CheckStatus.FAIL for result in results):
        return CheckStatus.FAIL

    if any(result.status == CheckStatus.WARNING for result in results):
        return CheckStatus.WARNING

    return CheckStatus.PASS


def _exit_code(status: CheckStatus) -> int:
    """Return the process exit code for a status."""
    if status == CheckStatus.FAIL:
        return EXIT_CODE_FAIL

    if status == CheckStatus.WARNING:
        return EXIT_CODE_WARNING

    return EXIT_CODE_PASS


def _status_text(status: CheckStatus) -> str:
    """Return a console friendly status text."""
    return status.value


def _github_symbol(status: CheckStatus) -> str:
    """Return a GitHub-friendly status symbol."""
    if status == CheckStatus.PASS:
        return "✅"

    if status == CheckStatus.WARNING:
        return "⚠️"

    return "❌"