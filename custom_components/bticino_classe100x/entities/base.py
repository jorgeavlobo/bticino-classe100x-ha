"""Base entity helpers for BTicino CLASSE100X entities."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import BticinoClasse100xCoordinator
from ..device import build_device_info


class BticinoClasse100xEntity(CoordinatorEntity[BticinoClasse100xCoordinator]):
    """Base entity for BTicino CLASSE100X entities.

    Centralizes the metadata shared by every platform so the individual entity
    classes only need to provide their entity description:

    * the device host, taken from the coordinator's config entry;
    * the stable unique ID and suggested object ID;
    * the translation key used for the entity name;
    * the shared device information.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the BTicino CLASSE100X base entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._host: str = coordinator.entry.data[CONF_HOST]

        # Most entities derive their unique-id suffix from the translation key.
        # The connection binary sensor keeps a legacy suffix that differs from
        # its key, so a description may override it via ``unique_key``.
        unique_key = getattr(description, "unique_key", None) or description.key

        self._attr_translation_key = description.key
        self._attr_unique_id = f"{DOMAIN}_{self._host}_{unique_key}"
        self._attr_suggested_object_id = f"{DOMAIN}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self.coordinator, self._host)
