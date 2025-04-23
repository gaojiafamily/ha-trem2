"""Diagnostics support for TREM2."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.components.system_log import LogErrorHandler
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

TO_REDACT = [
    CONF_API_TOKEN,
    CONF_EMAIL,
    CONF_PASSWORD,
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
):
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(hass, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: dr.DeviceEntry,
):
    """Return diagnostics for a device."""
    return _async_get_diagnostics(hass, entry)


@callback
def _async_get_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry):
    diag_data = {}

    try:
        system_log: LogErrorHandler = hass.data["system_log"]
        records = system_log.records.items()
        diag_data["title"] = config_entry.title
        diag_data["options"] = async_redact_data(config_entry.options, TO_REDACT)
        diag_data["logs"] = [entry.to_dict() for key, entry in records if DOMAIN in str(key)]
    except (AttributeError, KeyError, RuntimeError) as e:
        diag_data["error"] = "{e}: {reason}".format(
            e=e.name,
            reason=repr(e),
        )

    return diag_data
