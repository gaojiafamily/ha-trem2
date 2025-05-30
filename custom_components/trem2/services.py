"""Register services for the custom component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_SERVICE_DATA, CONF_URL, EntityCategory
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .const import ATTR_API_NODE, DOMAIN

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_register_services(hass: HomeAssistant) -> bool:
    """Register services for the custom component."""

    async def async_handle_simulate_earthquake(call: ServiceCall):
        """Handle the simulating earthquake service call."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        data = call.data.get(CONF_SERVICE_DATA, {})

        if not entity_id:
            raise HomeAssistantError("Entity ID is required")

        entity = er.async_get(hass)
        entry = entity.async_get(entity_id)

        if not entry or not entry.config_entry_id:
            raise HomeAssistantError(f"Entity ID {entity_id} not found")

        config_entry = cast(Trem2ConfigEntry, hass.config_entries.async_get_entry(entry.config_entry_id))

        if entry.entity_category == EntityCategory.DIAGNOSTIC:
            raise HomeAssistantError("Do not use this service for diagnostic entities")

        update_coordinator = config_entry.runtime_data.coordinator
        update_coordinator.data["recent"]["simulating"] = data

        if "eq" in data:
            _LOGGER.warning("Start earthquake simulation")
            hass.bus.fire(f"{DOMAIN}_notification", {"earthquake": data}, origin=EventOrigin.local)
            _LOGGER.debug("Simulating data: %s", data)
        else:
            _LOGGER.warning("Abort earthquake simulation")

    async def async_handle_set_http_node(call: ServiceCall):
        """Set the node specified by the user."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        base_url = call.data.get(CONF_URL)
        api_node = call.data.get(ATTR_API_NODE)

        if not entity_id:
            raise HomeAssistantError("Entity ID is required")

        entity = er.async_get(hass)
        entry = entity.async_get(entity_id)

        if not entry or not entry.config_entry_id:
            raise HomeAssistantError(f"Entity ID {entity_id} not found")

        config_entry = cast(Trem2ConfigEntry, hass.config_entries.async_get_entry(entry.config_entry_id))

        if entry.entity_category == EntityCategory.DIAGNOSTIC:
            raise HomeAssistantError("Do not use this service for diagnostic entities")

        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        update_coordinator = config_entry.runtime_data.coordinator
        if base_url:
            update_coordinator.update_interval = update_coordinator.conf.fast_interval
        else:
            update_coordinator.update_interval = update_coordinator.conf.base_interval

        update_coordinator.client.http.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        await update_coordinator.async_refresh()

        await update_coordinator.server_status_event(node=api_node or base_url)

    try:
        hass.services.async_register(
            DOMAIN,
            "simulator",
            async_handle_simulate_earthquake,
        )
        hass.services.async_register(
            DOMAIN,
            "set_http_node",
            async_handle_set_http_node,
        )
    except Exception as e:
        _LOGGER.error("Error registering services: %s", e)
        raise HomeAssistantError(f"Failed to register services: {e}") from e

    return True
