"""Find BTicino CLASSE100X references in Home Assistant storage files."""

from __future__ import annotations

import argparse
from pathlib import Path


SEARCH_TERMS: tuple[str, ...] = (
    "bticino",
    "bticino_classe100x",
    "condominium",
    "pedestrian",
)


def find_references(config_path: Path) -> None:
    """Print lines containing BTicino-related search terms."""
    storage_path = config_path / ".storage"

    if not storage_path.exists():
        print(f"Storage path not found: {storage_path}")
        return

    for path in storage_path.iterdir():
        if not path.is_file():
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(term in lowered for term in SEARCH_TERMS):
                print(f"{path}:{index}: {line}")


def main() -> None:
    """Run the reference finder."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config", help="Home Assistant config path")
    args = parser.parse_args()

    find_references(Path(args.config))


if __name__ == "__main__":
    main()
