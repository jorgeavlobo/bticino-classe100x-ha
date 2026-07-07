"""Health check result models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


def passed_result(name: str, details: list[str] | None = None) -> HealthCheckResult:
    """Create a passing health check result."""
    return HealthCheckResult(
        name=name,
        passed=True,
        details=details or [],
    )


def failed_result(
    name: str,
    errors: list[str],
    warnings: list[str] | None = None,
    details: list[str] | None = None,
) -> HealthCheckResult:
    """Create a failing health check result."""
    return HealthCheckResult(
        name=name,
        passed=False,
        errors=errors,
        warnings=warnings or [],
        details=details or [],
    )