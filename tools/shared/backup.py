"""Backup helpers for Home Assistant maintenance tools."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


def create_backup(path: Path) -> Path | None:
    """Create a timestamped backup next to the source file."""
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.backup_{timestamp}")

    shutil.copy2(path, backup_path)

    return backup_path
