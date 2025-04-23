"""Register services for the custom component."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.const import ATTR_ENTITY_ID, CONF_FILENAME, CONF_SERVICE_DATA, CONF_URL
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import async_get_platforms

from .const import ATTR_API_NODE, DOMAIN
from .update_coordinator import Trem2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_register_services(hass: HomeAssistant, coordinator: Trem2UpdateCoordinator):
    """Register services for the custom component."""
    hass.services.async_register(
        DOMAIN,
        "save2file",
        create_save_image_service(hass),
    )
    hass.services.async_register(
        DOMAIN,
        "simulator",
        create_simulating_earthquake_service(hass, coordinator),
    )
    hass.services.async_register(
        DOMAIN,
        "set_http_node",
        create_set_http_node_service(coordinator),
    )
    hass.services.async_register(
        DOMAIN,
        "set_ws_node",
        create_set_ws_node_service(coordinator),
    )


def create_save_image_service(hass: HomeAssistant):
    """Create the save image service."""

    async def save_image(call: ServiceCall):
        """Save image to file."""
        platforms = async_get_platforms(hass, DOMAIN)

        if len(platforms) < 1:
            raise HomeAssistantError(f"Integration not found: {DOMAIN}")

        entity_id = call.data.get(ATTR_ENTITY_ID)
        entity: ImageEntity | None = None
        for platform in platforms:
            entity_tmp: ImageEntity | None = platform.entities.get(entity_id, None)
            if entity_tmp is not None:
                entity = entity_tmp
                break
        if not entity:
            raise HomeAssistantError(f"Could not find entity {entity_id} from integration {DOMAIN}")

        filepath = Path(
            hass.config.path(
                call.data.get(
                    CONF_FILENAME,
                    f"www/{entity.extra_state_attributes.get('serial', DOMAIN)}",
                )
            )
        )

        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.suffix != ".png":
            filepath = filepath.with_suffix(".png")

        if not hass.config.is_allowed_path(str(filepath)):
            raise HomeAssistantError(
                f"Cannot write `{filepath!s}`, no access to path; "
                "`allowlist_external_dirs` may need to be adjusted in `configuration.yaml`"
            )

        image = await entity.async_image()
        try:
            await asyncio.to_thread(filepath.write_bytes, image)
            hass.bus.fire(f"{DOMAIN}_image_saved", {"filename": filepath.name})
        except OSError as e:
            raise HomeAssistantError(f"Failed to save image due to file error: {e}") from e

    return save_image


def create_simulating_earthquake_service(hass: HomeAssistant, coordinator: Trem2UpdateCoordinator):
    """Create the simulating earthquake service."""

    async def simulating_earthquake(call: ServiceCall):
        """Simulate an earthquake."""
        data = call.data.get(CONF_SERVICE_DATA, {})
        coordinator.state.simulating = data

        if "eq" in data:
            _LOGGER.warning("Start earthquake simulation")
            hass.bus.fire(f"{DOMAIN}_notification", {"earthquake": data}, origin=EventOrigin.local)
            _LOGGER.debug("Simulating data: %s", data)
        else:
            _LOGGER.warning("Abort earthquake simulation")

    return simulating_earthquake


def create_set_http_node_service(coordinator: Trem2UpdateCoordinator):
    """Create the set HTTP node service."""

    async def set_http_node(call: ServiceCall):
        """Set the node specified by the user."""
        api_node = call.data.get(ATTR_API_NODE)
        base_url = call.data.get(CONF_URL)

        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        if base_url:
            coordinator.update_interval = timedelta(seconds=1)
        else:
            coordinator.update_interval = coordinator.conf.base_interval

        await coordinator.http_client.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        await coordinator.async_refresh()

        coordinator.server_status_event()

    return set_http_node


def create_set_ws_node_service(coordinator: Trem2UpdateCoordinator):
    """Create the set WebSocket node service."""

    async def set_ws_node(call: ServiceCall):
        """Set the node specified by the user."""
        api_node = call.data.get(ATTR_API_NODE, None)
        base_url = call.data.get(CONF_URL, None)

        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        if not coordinator.ws_client.state.conn:
            raise HomeAssistantError("WebSocket is unavailable.")

        coordinator.update_interval = timedelta(seconds=1)
        await coordinator.ws_client.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        await coordinator.async_refresh()

        coordinator.server_status_event()

    return set_ws_node
