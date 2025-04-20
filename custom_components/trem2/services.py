"""Register services for the custom component."""

from __future__ import annotations

from datetime import timedelta
import asyncio
import logging
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import async_get_platforms

from .const import ATTR_API_URL, ATTR_API_NODE, ATTR_DATA, ATTR_SAVE2FILE, DOMAIN
from .update_coordinator import trem2_update_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_register_services(hass: HomeAssistant, coordinator: trem2_update_coordinator):
    """Register services for the custom component."""
    hass.services.async_register(DOMAIN, "save2file", create_save_image_service(hass))
    hass.services.async_register(DOMAIN, "simulator", create_simulating_earthquake_service(hass, coordinator))
    hass.services.async_register(DOMAIN, "set_http_node", create_set_http_node_service(hass, coordinator))
    hass.services.async_register(DOMAIN, "set_ws_node", create_set_ws_node_service(hass, coordinator))


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
                    ATTR_SAVE2FILE,
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
            raise HomeAssistantError(f"Failed to save image due to file error: {e}")

    return save_image


def create_simulating_earthquake_service(hass: HomeAssistant, coordinator: trem2_update_coordinator):
    """Create the simulating earthquake service."""

    async def simulating_earthquake(call: ServiceCall):
        """Simulate an earthquake."""
        data = call.data.get(ATTR_DATA, "")
        coordinator.simulating_notification = data

        if data == "":
            _LOGGER.warning("Abort earthquake simulation")
            return

        _LOGGER.warning("Start earthquake simulation")
        hass.bus.fire(f"{DOMAIN}_notification", {"earthquake": data}, origin=EventOrigin.local)

    return simulating_earthquake


def create_set_http_node_service(hass: HomeAssistant, coordinator: trem2_update_coordinator):
    """Create the set HTTP node service."""

    async def set_http_node(call: ServiceCall):
        """Set the node specified by the user."""
        base_url = call.data.get(ATTR_API_URL)
        station = call.data.get(ATTR_API_NODE)

        if base_url is None and station is None:
            raise ServiceValidationError("Both `Server URL` and `node station` must be provided.")

        if base_url:
            coordinator.update_interval = timedelta(seconds=1)
        else:
            coordinator.update_interval = coordinator.base_interval

        coordinator._initialize_task = None
        await coordinator.http_manager.initialize_route(
            base_url=base_url,
            station=station,
        )
        await coordinator.async_refresh()

        event_data = {
            "type": "server_status",
            "current_node": station,
            "cust_url": base_url,
            "protocol": "http",
        }
        hass.bus.fire(f"{DOMAIN}_status", event_data)

    return set_http_node


def create_set_ws_node_service(hass: HomeAssistant, coordinator: trem2_update_coordinator):
    """Create the set WebSocket node service."""

    async def set_ws_node(call: ServiceCall):
        """Set the node specified by the user."""
        base_url = call.data.get(ATTR_API_URL, None)
        station = call.data.get(ATTR_API_NODE, None)

        if base_url is None and station is None:
            raise ServiceValidationError("Missing `Server URL` or `node station`.")

        if not coordinator.http_manager.websocket:
            raise HomeAssistantError("WebSocket is unavailable.")

        coordinator._initialize_task = None
        coordinator.update_interval - timedelta(seconds=1)
        await coordinator.ws_manager.initialize_route(
            base_url=base_url,
            station=station,
        )
        await coordinator.async_refresh()

        event_data = {
            "type": "server_status",
            "current_node": station,
            "cust_url": base_url,
            "protocol": "ws",
        }
        hass.bus.fire(f"{DOMAIN}_status", event_data)

    return set_ws_node
