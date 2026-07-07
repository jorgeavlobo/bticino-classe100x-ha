"""JSON file helpers for BTicino CLASSE100X maintenance tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file and return its decoded object."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON object to disk using stable formatting."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
