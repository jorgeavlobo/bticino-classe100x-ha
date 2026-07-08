"""Shared HACS-detection constants and helpers.

HACS creates its own management entities for the integration (an ``update``
entity and a ``pre_release`` switch). Their entity_id and unique_id embed the
integration name but they belong to HACS, not to this integration, so the
maintenance and diagnostic tools must never treat them as BTicino entries.

This is the single source of truth for HACS detection, shared by both
``tools/shared/matching.py`` (cleanup tools) and
``tools/diagnostics/shared/entities.py`` (health check), so the two never drift.
"""

from __future__ import annotations

from typing import Any

HACS_PLATFORM = "hacs"

# HACS management entities created for the BTicino integration.
HACS_ENTITY_ID_PREFIXES: tuple[str, ...] = (
    "update.bticino_classe100x",
    "switch.bticino_classe100x",
)


def is_hacs_platform(entity: Any) -> bool:
    """Return true when a registry entity's platform is HACS."""
    return isinstance(entity, dict) and entity.get("platform") == HACS_PLATFORM
