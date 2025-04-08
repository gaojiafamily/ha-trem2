"""Custom Image Display integration for Home Assistant."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    PLATFORMS,
    STARTUP,
    STORAGE_EEW,
    TREM2_COORDINATOR,
    TREM2_NAME,
    UPDATE_LISTENER,
)
from .update_coordinator import trem2_update_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Custom Image Display from a config entry."""
    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data={}, options=entry.data)

    # Store the config entry data in hass.data
    hass.data.setdefault(DOMAIN, {})
    domain_data: dict = {}

    store = Store(hass, 1, STORAGE_EEW)
    update_coordinator = trem2_update_coordinator(
        hass,
        timedelta(seconds=5),
        store,
    )
    domain_data = {
        TREM2_COORDINATOR: update_coordinator,
        TREM2_NAME: DEFAULT_NAME,
    }

    # Set up the coordinator
    await update_coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = domain_data

    # Set up the coordinator listener
    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener

    # Set up the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(STARTUP)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
