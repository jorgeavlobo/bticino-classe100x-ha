"""Base entity helpers for BTicino CLASSE100X entities."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import BticinoClasse100xCoordinator
from ..device import build_device_info


class BticinoClasse100xEntity(CoordinatorEntity[BticinoClasse100xCoordinator]):
    """Base entity for BTicino CLASSE100X entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        host: str,
        key: str,
        icon: str | None = None,
        entity_category: EntityCategory | None = None,
        unique_key: str | None = None,
    ) -> None:
        """Initialize the BTicino CLASSE100X base entity."""
        super().__init__(coordinator)

        resolved_unique_key = unique_key or key

        self._host = host
        self._attr_icon = icon
        self._attr_translation_key = key
        self._attr_unique_id = f"{DOMAIN}_{host}_{resolved_unique_key}"
        self._attr_suggested_object_id = f"{DOMAIN}_{key}"
        self._attr_entity_category = entity_category

    @property
    def device_info(self):
        """Return device information."""
        return build_device_info(self.coordinator, self._host)


def get_host_from_entry(entry) -> str:
    """Return the configured host from a config entry."""
    return entry.data[CONF_HOST]