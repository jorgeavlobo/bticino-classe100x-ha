"""Storage helpers for Home Assistant health checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_file(path: Path) -> dict[str, Any]:
    """Read a Home Assistant JSON storage file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def storage_file(config_path: Path, filename: str) -> Path:
    """Return a file inside the Home Assistant .storage folder."""
    return config_path / ".storage" / filename


def read_storage_list(config_path: Path, filename: str, key: str) -> list[dict[str, Any]]:
    """Read a list from a Home Assistant storage file."""
    path = storage_file(config_path, filename)

    if not path.exists():
        return []

    data = read_json_file(path)

    value = data.get("data", {}).get(key, [])

    if isinstance(value, list):
        return value

    return []