"""Config flow to configure TREM2 component."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import CONN_CLASS_CLOUD_POLL, ConfigFlow

from .const import DEFAULT_NAME, DOMAIN


class TREM2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for trem2."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            user_input = {}

        await self.async_set_unique_id(f"{DOMAIN}_monitoring")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_reauth(self, user_input=None):
        """Handle reauthorization if needed."""
        if user_input is not None:
            return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
            }),
            errors=self._errors,
        )
