"""Register services for the custom component."""

from __future__ import annotations

from typing import cast, TYPE_CHECKING

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_SERVICE_DATA, CONF_URL, EntityCategory
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry

from .const import ATTR_API_NODE, DOMAIN

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_register_services(hass: HomeAssistant) -> bool:  # noqa: C901
    """Register services for the custom component."""
    hass.services.async_register(DOMAIN, "save2file", create_save_image_service(hass))
    hass.services.async_register(DOMAIN, "simulator", create_simulating_earthquake_service(hass, coordinator))
    hass.services.async_register(DOMAIN, "set_http_node", create_set_http_node_service(hass, coordinator))
    hass.services.async_register(DOMAIN, "set_ws_node", create_set_ws_node_service(hass, coordinator))


def create_save_image_service(hass: HomeAssistant):
    """Create the save image service."""

    async def async_handle_simulate_earthquake(call: ServiceCall):
        """Handle the simulating earthquake service call."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        data = call.data.get(CONF_SERVICE_DATA, {})

        if not entity_id:
            raise HomeAssistantError("Entity ID is required")

        er = entity_registry.async_get(hass)
        entry = er.async_get(entity_id)

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

        er = entity_registry.async_get(hass)
        entry = er.async_get(entity_id)

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
