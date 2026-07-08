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

import re
from typing import Any, Iterable

HACS_PLATFORM = "hacs"

# The exact entity ids HACS creates for the BTicino integration. Matched by
# equality (never as a prefix) in ``matching.is_hacs_managed`` as the fallback
# for restore-state entries, which do not carry a ``platform`` field. Using the
# full ids and exact matching means a genuine BTicino ``update``/``switch``
# entity following the ``bticino_classe100x_<key>`` convention (for example a
# future ``switch.bticino_classe100x_intercom_mute``, or a suffixed
# ``update.bticino_classe100x_update_2``) is never misclassified as
# HACS-managed.
HACS_ENTITY_IDS: frozenset[str] = frozenset(
    {
        "update.bticino_classe100x_update",
        "switch.bticino_classe100x_pre_release",
    }
)


def is_hacs_platform(entity: Any) -> bool:
    """Return true when a registry entity's platform is HACS."""
    return isinstance(entity, dict) and entity.get("platform") == HACS_PLATFORM


def strip_hacs_entity_ids(
    text: str, entity_ids: Iterable[str] = HACS_ENTITY_IDS
) -> str:
    """Remove HACS entity ids from ``text``, matching whole entity ids only.

    Each id is removed only where it is not part of a longer entity id — not
    directly preceded or followed by an entity-id word character — so a suffixed
    id such as ``update.bticino_classe100x_update_2`` (a genuine, non-HACS
    entity Home Assistant may create) is left intact and still matches the
    BTicino token afterwards. Used to neutralize HACS-only references before the
    token text scan in both the cleanup matcher and the reference scanner.
    """
    for entity_id in entity_ids:
        text = re.sub(rf"(?<!\w){re.escape(entity_id)}(?!\w)", "", text)
    return text
