"""Base classes for health checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .result import HealthCheckResult


class HealthCheck(ABC):
    """Base class for a health check."""

    name: str
    description: str

    @abstractmethod
    def run(self, config_path: Path) -> HealthCheckResult:
        """Run the health check."""