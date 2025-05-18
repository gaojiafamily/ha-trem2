"""Register services for the custom component."""

from __future__ import annotations

import logging

from homeassistant.const import ATTR_ENTITY_ID, CONF_SERVICE_DATA, CONF_URL, EntityCategory
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry


from .const import ATTR_API_NODE, DOMAIN, UPDATE_COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_register_services(hass: HomeAssistant):
    """Register services for the custom component."""

    async def async_handle_simulate_earthquake(call: ServiceCall):
        """Handle the simulating earthquake service call."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        data = call.data.get(CONF_SERVICE_DATA, {})

        # Check if the entity ID is valid
        if not entity_id:
            raise HomeAssistantError("Entity ID is required")

        # Get the entity registry
        er_register = entity_registry.async_get(hass)
        entry = er_register.async_get(entity_id)

        # Check if the entity ID exists in the registry
        if not entry:
            raise HomeAssistantError(f"Entity ID {entity_id} not found")

        # Check if the entity is a sensor
        if entry.entity_category == EntityCategory.DIAGNOSTIC:
            raise HomeAssistantError("Do not use this service for diagnostic entities")

        coordinator = hass.data[DOMAIN][entry.config_entry_id][UPDATE_COORDINATOR]
        coordinator.state.simulating = data

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

        # Check if the entity ID is valid
        if not entity_id:
            raise HomeAssistantError("Entity ID is required")

        # Get the entity registry
        er_register = entity_registry.async_get(hass)
        entry = er_register.async_get(entity_id)

        # Check if the entity ID exists in the registry
        if not entry:
            raise HomeAssistantError(f"Entity ID {entity_id} not found")

        # Check if the entity is a sensor
        if entry.entity_category == EntityCategory.DIAGNOSTIC:
            raise HomeAssistantError("Do not use this service for diagnostic entities")

        # Validity of the base_url and api_node
        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        coordinator = hass.data[DOMAIN][entry.config_entry_id][UPDATE_COORDINATOR]
        if base_url:
            coordinator.update_interval = coordinator.conf.fast_interval
        else:
            coordinator.update_interval = coordinator.conf.base_interval

        coordinator.http_client.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        await coordinator.async_refresh()

        coordinator.server_status_event(node=api_node or base_url)

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
