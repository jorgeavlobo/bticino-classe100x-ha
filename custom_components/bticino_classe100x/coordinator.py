"""Data coordinator for BTicino CLASSE100X."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_AUTH_METHOD,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_RELEASE_DELAY,
    CONF_SSH_KEY_PATH,
    DOMAIN,
    TEST_RESULT_FAILED,
    TEST_RESULT_SUCCESS,
)
from .api.openwebnet import (
    BticinoConnectionConfig,
    BticinoOpenWebNetClient,
    BticinoOpenWebNetError,
)

from .api.device_information import (
    BticinoDeviceInformation,
    BticinoDeviceInformationClient,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)


class BticinoClasse100xCoordinator(DataUpdateCoordinator[bool]):
    """Coordinator that checks BTicino CLASSE100X availability."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry

        config = {
            **entry.data,
            **entry.options,
        }

        connection_config = BticinoConnectionConfig(
            host=config[CONF_HOST],
            username=config[CONF_USERNAME],
            auth_method=config.get(CONF_AUTH_METHOD, "ssh_key"),
            ssh_key_path=config.get(CONF_SSH_KEY_PATH),
            password=config.get(CONF_PASSWORD),
            command_timeout=config.get(CONF_COMMAND_TIMEOUT, 10),
            release_delay=config.get(CONF_RELEASE_DELAY, 1.0),
        )

        self.client = BticinoOpenWebNetClient(connection_config)
        self.device_information_client = BticinoDeviceInformationClient(connection_config)
        self.device_information = BticinoDeviceInformation()
        self.last_error: str | None = None
        self.last_test_result: str | None = None
        self.last_test_time: str | None = None
        self.last_successful_test_time: str | None = None
        self.last_failed_test_time: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

    async def async_run_connection_test(self) -> bool:
        """Run a full manual connection test and update coordinator state."""
        self.last_test_time = datetime.now().isoformat(timespec="seconds")

        try:
            is_connected = await self.hass.async_add_executor_job(
                self.client.test_connection
            )
        except BticinoOpenWebNetError as exc:
            self.last_error = str(exc)
            self.last_test_result = TEST_RESULT_FAILED
            self.last_failed_test_time = self.last_test_time
            self.async_set_updated_data(False)
            return False

        if not is_connected:
            self.last_error = "OpenWebNet did not return a valid response"
            self.last_test_result = TEST_RESULT_FAILED
            self.last_failed_test_time = self.last_test_time
            self.async_set_updated_data(False)
            return False

        self.device_information = await self.hass.async_add_executor_job(
            self.device_information_client.collect
        )

        self.device_information.openwebnet_latency_ms = await self.hass.async_add_executor_job(
            self.client.measure_latency_ms
        )

        self.last_error = None
        self.last_test_result = TEST_RESULT_SUCCESS
        self.last_successful_test_time = self.last_test_time
        self.async_set_updated_data(True)

        return True

    async def _async_update_data(self) -> bool:
        """Check if the CLASSE100X is reachable and collect device information."""
        self.last_test_time = datetime.now().isoformat(timespec="seconds")

        try:
            is_connected = await self.hass.async_add_executor_job(
                self.client.test_connection
            )
        except BticinoOpenWebNetError as exc:
            self.last_error = str(exc)
            self.last_test_result = TEST_RESULT_FAILED
            self.last_failed_test_time = self.last_test_time
            _LOGGER.warning("BTicino CLASSE100X connection check failed: %s", exc)
            return False

        if not is_connected:
            self.last_error = "OpenWebNet did not return a valid response"
            self.last_test_result = TEST_RESULT_FAILED
            self.last_failed_test_time = self.last_test_time
            return False

        self.last_error = None
        self.last_test_result = TEST_RESULT_SUCCESS
        self.last_successful_test_time = self.last_test_time

        self.device_information = await self.hass.async_add_executor_job(
            self.device_information_client.collect
        )

        self.device_information.openwebnet_latency_ms = await self.hass.async_add_executor_job(
            self.client.measure_latency_ms
        )

        return True
