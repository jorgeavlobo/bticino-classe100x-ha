"""Button entities for BTicino CLASSE100X."""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..api.openwebnet import BticinoOpenWebNetError
from ..const import (
    BUTTON_TYPE_COMMAND,
    BUTTON_TYPE_TEST,
    CONDOMINIUM_GATE_PRESS_COMMAND,
    CONDOMINIUM_GATE_RELEASE_COMMAND,
    DOMAIN,
    PEDESTRIAN_DOOR_PRESS_COMMAND,
    PEDESTRIAN_DOOR_RELEASE_COMMAND,
)
from ..coordinator import BticinoClasse100xCoordinator
from .base import BticinoClasse100xEntity, get_host_from_entry
from .descriptions import BticinoButtonDescription

_LOGGER = logging.getLogger(__name__)


BUTTON_DESCRIPTIONS: tuple[BticinoButtonDescription, ...] = (
    BticinoButtonDescription(
        key="condominium_gate",
        icon="mdi:gate",
        button_type=BUTTON_TYPE_COMMAND,
        press_command=CONDOMINIUM_GATE_PRESS_COMMAND,
        release_command=CONDOMINIUM_GATE_RELEASE_COMMAND,
    ),
    BticinoButtonDescription(
        key="pedestrian_door",
        icon="mdi:door",
        button_type=BUTTON_TYPE_COMMAND,
        press_command=PEDESTRIAN_DOOR_PRESS_COMMAND,
        release_command=PEDESTRIAN_DOOR_RELEASE_COMMAND,
    ),
    BticinoButtonDescription(
        key="test_ssh_connection",
        icon="mdi:lan-check",
        button_type=BUTTON_TYPE_TEST,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BTicino CLASSE100X buttons from a config entry."""
    coordinator: BticinoClasse100xCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = get_host_from_entry(entry)

    async_add_entities(
        [
            BticinoClasse100xButton(
                coordinator=coordinator,
                host=host,
                description=description,
            )
            for description in BUTTON_DESCRIPTIONS
        ]
    )


class BticinoClasse100xButton(BticinoClasse100xEntity, ButtonEntity):
    """Representation of a BTicino CLASSE100X button."""

    def __init__(
        self,
        coordinator: BticinoClasse100xCoordinator,
        host: str,
        description: BticinoButtonDescription,
    ) -> None:
        """Initialize the BTicino CLASSE100X button."""
        super().__init__(
            coordinator=coordinator,
            host=host,
            key=description.key,
            icon=description.icon,
            entity_category=description.entity_category,
        )

        self._description = description

    @property
    def available(self) -> bool:
        """Return true when the button can be used."""
        if self._description.button_type == BUTTON_TYPE_TEST:
            return True

        return bool(self.coordinator.data)

    async def async_press(self) -> None:
        """Press the BTicino button."""
        if self._description.button_type == BUTTON_TYPE_TEST:
            await self._async_test_connection()
            return

        await self._async_send_openwebnet_sequence()

    async def _async_send_openwebnet_sequence(self) -> None:
        """Send the OpenWebNet press/release command sequence."""
        if (
            self._description.press_command is None
            or self._description.release_command is None
        ):
            raise HomeAssistantError("BTicino button command is not configured")

        try:
            await self.coordinator.hass.async_add_executor_job(
                self.coordinator.client.send_sequence,
                self._description.press_command,
                self._description.release_command,
                self.name,
            )

            await self.coordinator.async_request_refresh()

        except BticinoOpenWebNetError as exc:
            _LOGGER.error("Failed to press BTicino button '%s': %s", self.name, exc)
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(
                f"Failed to press BTicino button '{self.name}'"
            ) from exc

    async def _async_test_connection(self) -> None:
        """Manually test the BTicino CLASSE100X SSH/OpenWebNet connection."""
        _LOGGER.info("Testing BTicino CLASSE100X SSH/OpenWebNet connection")

        is_connected = await self.coordinator.async_run_connection_test()

        if not is_connected:
            persistent_notification.async_create(
                self.coordinator.hass,
                f"Connection test failed: {self.coordinator.last_error}",
                title="BTicino CLASSE100X",
                notification_id="bticino_classe100x_connection_test",
            )

            raise HomeAssistantError("BTicino CLASSE100X connection test failed")

        persistent_notification.async_create(
            self.coordinator.hass,
            "Connection test succeeded.",
            title="BTicino CLASSE100X",
            notification_id="bticino_classe100x_connection_test",
        )

        _LOGGER.info("BTicino CLASSE100X connection test succeeded")