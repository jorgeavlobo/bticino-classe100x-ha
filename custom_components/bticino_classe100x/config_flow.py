"""Config flow and options flow for BTicino CLASSE100X."""

from __future__ import annotations

import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    AUTH_METHOD_PASSWORD,
    AUTH_METHOD_SSH_KEY,
    CONF_AUTH_METHOD,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_RELEASE_DELAY,
    CONF_SSH_KEY_PATH,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_RELEASE_DELAY,
    DEFAULT_SSH_KEY_PATH,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .api.openwebnet import (
    BticinoConnectionConfig,
    BticinoOpenWebNetClient,
    BticinoOpenWebNetError,
)


async def _file_exists(hass: HomeAssistant, file_path: str) -> bool:
    """Check whether a file exists inside Home Assistant."""
    return await hass.async_add_executor_job(os.path.isfile, file_path)


async def _validate_connection(hass: HomeAssistant, user_input: dict[str, Any]) -> str | None:
    """Validate SSH/OpenWebNet connectivity.

    Returns:
        None when validation succeeds, otherwise a translation error key.
    """
    auth_method = user_input[CONF_AUTH_METHOD]

    if auth_method == AUTH_METHOD_PASSWORD:
        return "password_auth_not_implemented"

    ssh_key_path = user_input.get(CONF_SSH_KEY_PATH)

    if not ssh_key_path:
        return "ssh_key_required"

    if not await _file_exists(hass, ssh_key_path):
        return "ssh_key_not_found"

    client = BticinoOpenWebNetClient(
        BticinoConnectionConfig(
            host=user_input[CONF_HOST],
            username=user_input[CONF_USERNAME],
            auth_method=auth_method,
            ssh_key_path=ssh_key_path,
            password=user_input.get(CONF_PASSWORD),
            command_timeout=user_input.get(CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT),
            release_delay=user_input.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY),
        )
    )

    try:
        connected = await hass.async_add_executor_job(client.test_connection)
    except BticinoOpenWebNetError:
        return "cannot_connect"

    if not connected:
        return "openwebnet_no_response"

    return None


def _auth_method_selector() -> SelectSelector:
    """Return the authentication method selector.

    The option labels are translated through the ``auth_method`` selector
    translation key, so no user-visible strings are hardcoded here.
    """
    return SelectSelector(
        SelectSelectorConfig(
            options=[AUTH_METHOD_SSH_KEY, AUTH_METHOD_PASSWORD],
            translation_key="auth_method",
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the configuration/options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME),
            ): str,
            vol.Required(
                CONF_AUTH_METHOD,
                default=defaults.get(CONF_AUTH_METHOD, AUTH_METHOD_SSH_KEY),
            ): _auth_method_selector(),
            vol.Optional(
                CONF_SSH_KEY_PATH,
                default=defaults.get(CONF_SSH_KEY_PATH, DEFAULT_SSH_KEY_PATH),
            ): str,
            vol.Optional(CONF_PASSWORD): str,
            vol.Required(
                CONF_COMMAND_TIMEOUT,
                default=defaults.get(CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT),
            ): vol.Coerce(int),
            vol.Required(
                CONF_RELEASE_DELAY,
                default=defaults.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY),
            ): vol.Coerce(float),
        }
    )


class BticinoClasse100xConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BTicino CLASSE100X."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        """Create the options flow."""
        return BticinoClasse100xOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            validation_error = await _validate_connection(self.hass, user_input)

            if validation_error is None:
                return self.async_create_entry(
                    title="BTicino CLASSE100X",
                    data=user_input,
                )

            errors["base"] = validation_error

        defaults = {
            CONF_HOST: "192.168.50.251",
            CONF_USERNAME: DEFAULT_USERNAME,
            CONF_AUTH_METHOD: AUTH_METHOD_SSH_KEY,
            CONF_SSH_KEY_PATH: DEFAULT_SSH_KEY_PATH,
            CONF_COMMAND_TIMEOUT: DEFAULT_COMMAND_TIMEOUT,
            CONF_RELEASE_DELAY: DEFAULT_RELEASE_DELAY,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors=errors,
        )


class BticinoClasse100xOptionsFlow(config_entries.OptionsFlow):
    """Handle options for BTicino CLASSE100X."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        """Manage BTicino CLASSE100X options."""
        errors: dict[str, str] = {}

        current = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        if user_input is not None:
            validation_error = await _validate_connection(self.hass, user_input)

            if validation_error is None:
                return self.async_create_entry(
                    title="",
                    data=user_input,
                )

            errors["base"] = validation_error

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current),
            errors=errors,
        )
