"""Path helpers for Home Assistant storage files."""

from __future__ import annotations

from pathlib import Path


def storage_path(config_path: Path) -> Path:
    """Return the Home Assistant .storage directory."""
    return config_path / ".storage"


def entity_registry_path(config_path: Path) -> Path:
    """Return the Home Assistant entity registry path."""
    return storage_path(config_path) / "core.entity_registry"


def restore_state_path(config_path: Path) -> Path:
    """Return the Home Assistant restore state path."""
    return storage_path(config_path) / "core.restore_state"


def config_entries_path(config_path: Path) -> Path:
    """Return the Home Assistant config entries path."""
    return storage_path(config_path) / "core.config_entries"


def device_registry_path(config_path: Path) -> Path:
    """Return the Home Assistant device registry path."""
    return storage_path(config_path) / "core.device_registry"
