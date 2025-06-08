"""Diagnostics support for TREM2."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.components.system_log import LogErrorHandler
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData


TO_REDACT = [
    CONF_API_TOKEN,
    CONF_EMAIL,
    CONF_PASSWORD,
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: Trem2ConfigEntry,
):
    """Return diagnostics for a config entry."""
    return await _async_get_diagnostics(hass, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: Trem2ConfigEntry,
    device: dr.DeviceEntry,
):
    """Return diagnostics for a device."""
    return await _async_get_diagnostics(hass, entry)


async def _async_get_diagnostics(hass: HomeAssistant, config_entry: Trem2ConfigEntry):
    diag_data = {}
    runtime_data = config_entry.runtime_data
    coordinator = runtime_data.coordinator

    try:
        system_log: LogErrorHandler = hass.data["system_log"]
        records = system_log.records.items()
        diag_data["title"] = config_entry.title
        diag_data["options"] = async_redact_data(config_entry.options, TO_REDACT)
        diag_data["logs"] = [entry.to_dict() for key, entry in records if config_entry.domain in str(key)]

        if coordinator:
            diag_data["last_exception"] = repr(coordinator.last_exception)
            diag_data["server_status"] = await coordinator.data_client.server_status()
            diag_data["recent"] = coordinator.data["recent"]
            diag_data["report"] = coordinator.data["report"]
            diag_data["update_interval"] = runtime_data.update_interval.total_seconds()
    except (AttributeError, KeyError, RuntimeError) as e:
        diag_data["error"] = f"{type(e).__name__}: {e!r}"

    return diag_data
