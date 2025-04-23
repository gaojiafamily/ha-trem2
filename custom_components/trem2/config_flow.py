"""Config flow to configure TREM2 component."""

from __future__ import annotations

import json

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_POST, USER_AGENT
import voluptuous as vol

from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    HANDLERS,
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.const import (
    APPLICATION_NAME,
    CONF_API_TOKEN,
    CONF_EMAIL,
    CONF_NAME,
    CONF_PASSWORD,
    CONTENT_TYPE_JSON,
    __version__ as HAVERSION,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CLIENT_NAME,
    CONF_PASS,
    CONF_PROVIDER,
    DOMAIN,
    HA_USER_AGENT,
    LOGIN_URL,
    PROVIDER_OPTIONS,
    REQUEST_TIMEOUT,
    SOURCE_INIT,
    __version__ as CLIENT_VER,
)


@HANDLERS.register(DOMAIN)
class TREM2FlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for trem2."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Initialize config flow form
        if user_input is None:
            return self.async_show_form(
                step_id=SOURCE_USER,
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_EMAIL): str,
                        vol.Optional(CONF_PASSWORD): str,
                        vol.Required(CONF_PROVIDER): vol.In([x[0] for x in PROVIDER_OPTIONS]),
                    }
                ),
            )

        # ExpTech account and password validation
        if CONF_EMAIL in user_input:
            return await self.async_step_external_auth(user_input)

        # Create entry if it does not already exist
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="ExpTech User", data=user_input)

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle re-authentication."""
        error = {}

        # Dialog that informs the user that reauth is required
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )

        # ExpTech account and password validation
        if CONF_EMAIL in user_input:
            session = async_get_clientsession(self.hass)
            result = await _verify(session, user_input)

            # Download ExpTech certification if validation success
            if result["success"]:
                user_input[CONF_API_TOKEN] = result[CONF_API_TOKEN]
                self.hass.config_entries.async_update_entry(
                    self._get_reauth_entry(),
                    data=user_input,
                )

                return self.async_abort(reason="reauth_successful")
            else:
                error["base"] = result.get("error", "reauth_failed")

        return self.async_show_form(
            step_id=SOURCE_REAUTH,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_PROVIDER): vol.In([x[0] for x in PROVIDER_OPTIONS]),
                }
            ),
            errors=error,
        )

    async def async_step_external_auth(self, user_input=None):
        """Verify ExpTech certification."""
        if user_input is None:
            user_input = {}

        # Download ExpTech certification if validation success
        session = async_get_clientsession(self.hass)
        result = await _verify(session, user_input)
        if result["success"]:
            await self.async_set_unique_id(
                "{prefix}_{suffix}".format(
                    prefix=DOMAIN,
                    suffix=result[CONF_API_TOKEN],
                )
            )
            self._abort_if_unique_id_configured()

            user_input[CONF_API_TOKEN] = result[CONF_API_TOKEN]
            return self.async_create_entry(title="ExpTech VIP", data=user_input)

        # Request to re-enter ExpTech account and password
        return self.async_show_form(
            step_id=SOURCE_USER,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_PROVIDER, default=user_input.get(CONF_PROVIDER, "")): vol.In(
                        [x[0] for x in PROVIDER_OPTIONS]
                    ),
                }
            ),
            errors={"base": result.get("error", "unknown")},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get option flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle options flow changes."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is None:
            return self.async_show_form(
                step_id=SOURCE_INIT,
                data_schema=self.add_suggested_values_to_schema(
                    vol.Schema(
                        {
                            vol.Optional(CONF_EMAIL): str,
                            vol.Optional(CONF_PASSWORD): str,
                            vol.Required(CONF_PROVIDER): vol.In([x[0] for x in PROVIDER_OPTIONS]),
                        }
                    ),
                    self.config_entry.options,
                ),
            )

        # ExpTech account and password validation
        if CONF_EMAIL in user_input:
            return await self.async_step_external_auth(user_input)
        else:
            self.hass.config_entries.async_update_entry(self.config_entry, title="ExpTech User")

        # Create entry if it does not already exist
        return self.async_create_entry(title=self.config_entry.title, data=user_input)

    async def async_step_external_auth(self, user_input=None):
        """Verify ExpTech certification."""
        if user_input is None:
            user_input = {}

        # Download ExpTech certification if validation success
        session = async_get_clientsession(self.hass)
        result = await _verify(session, user_input)
        if result["success"]:
            user_input[CONF_API_TOKEN] = result[CONF_API_TOKEN]
            self.hass.config_entries.async_update_entry(self.config_entry, title="ExpTech VIP")
            return self.async_create_entry(title=self.config_entry.title, data=user_input)

        # Request to re-enter ExpTech account and password
        return self.async_show_form(
            step_id=SOURCE_INIT,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_PROVIDER, default=user_input.get(CONF_PROVIDER, "")): vol.In(
                        [x[0] for x in PROVIDER_OPTIONS]
                    ),
                }
            ),
            errors={"base": result.get("error", "unknown")},
        )


async def _verify(session: ClientSession, user_input: dict) -> dict:
    result = {
        "success": False,
        "error": "unknown",
    }

    if CONF_EMAIL in user_input and CONF_PASSWORD in user_input:
        try:
            payload = {
                CONF_EMAIL: user_input[CONF_EMAIL],
                CONF_PASS: user_input[CONF_PASSWORD],
                CONF_NAME: f"{APPLICATION_NAME}/{CLIENT_NAME}/{CLIENT_VER}/{HAVERSION}",
            }
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }
            resp = await session.request(
                method=METH_POST,
                url=LOGIN_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError):
            result["error"] = "cannot_connect"
        else:
            if resp.ok:
                result["success"] = True
                result["error"] = ""
                result[CONF_API_TOKEN] = await resp.text()

            if resp.status == 401:
                result["error"] = "invalid_auth"
    else:
        result["error"] = "invalid_auth"

    return result
