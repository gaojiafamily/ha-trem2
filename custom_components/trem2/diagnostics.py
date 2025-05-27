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
    from .image import MonitoringImage
    from .runtime import Trem2RuntimeData
    from .update_coordinator import Trem2UpdateCoordinator


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
    update_coordinator: Trem2UpdateCoordinator = config_entry.runtime_data.coordinator

    try:
        system_log: LogErrorHandler = hass.data["system_log"]
        records = system_log.records.items()
        diag_data["title"] = config_entry.title
        diag_data["options"] = async_redact_data(config_entry.options, TO_REDACT)
        diag_data["logs"] = [entry.to_dict() for key, entry in records if config_entry.domain in str(key)]

        if update_coordinator:
            diag_data["use_http_fallback"] = update_coordinator.client.use_http_fallback
            diag_data["last_exception"] = repr(update_coordinator.last_exception)
            diag_data["server_status"] = await update_coordinator.client.server_status()
            diag_data["recent"] = update_coordinator.data["recent"]
            diag_data["report"] = update_coordinator.data["report"]

        entities = hass.data[config_entry.domain][config_entry.entry_id]
        if "monitoring" in entities:
            image_entity: MonitoringImage = entities["monitoring"]
            diag_data[config_entry.entry_id] = {"intensitys": image_entity.data.intensitys}
    except (AttributeError, KeyError, RuntimeError) as e:
        diag_data["error"] = f"{type(e).__name__}: {e!r}"

    return diag_data
