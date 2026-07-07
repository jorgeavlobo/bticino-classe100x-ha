"""Health check result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CheckStatus(StrEnum):
    """Health check status."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(slots=True)
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: CheckStatus
    summary: str
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return true when the check passed."""
        return self.status == CheckStatus.PASS

    @property
    def failed(self) -> bool:
        """Return true when the check failed."""
        return self.status == CheckStatus.FAIL


def pass_result(
    name: str,
    summary: str,
    details: list[str] | None = None,
) -> HealthCheckResult:
    """Create a passing health check result."""
    return HealthCheckResult(
        name=name,
        status=CheckStatus.PASS,
        summary=summary,
        details=details or [],
    )


def warning_result(
    name: str,
    summary: str,
    warnings: list[str],
    details: list[str] | None = None,
) -> HealthCheckResult:
    """Create a warning health check result."""
    return HealthCheckResult(
        name=name,
        status=CheckStatus.WARNING,
        summary=summary,
        warnings=warnings,
        details=details or [],
    )


def fail_result(
    name: str,
    summary: str,
    errors: list[str],
    warnings: list[str] | None = None,
    details: list[str] | None = None,
) -> HealthCheckResult:
    """Create a failing health check result."""
    return HealthCheckResult(
        name=name,
        status=CheckStatus.FAIL,
        summary=summary,
        errors=errors,
        warnings=warnings or [],
        details=details or [],
    )