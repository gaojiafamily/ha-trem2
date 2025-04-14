"""Register services for the custom component."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .const import ATTR_DATA, ATTR_SAVE2FILE, DOMAIN

from homeassistant.components.image import ImageEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import EventOrigin, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import async_get_platforms

from .update_coordinator import trem2_update_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_register_services(
    hass: HomeAssistant, coordinator: trem2_update_coordinator, domain: str
):
    """Register services for the custom component."""

    async def save_image(call: ServiceCall):
        """Save image to file."""
        platforms = async_get_platforms(hass, DOMAIN)

        # Check if the platforms are available
        if len(platforms) < 1:
            raise HomeAssistantError(f"Integration not found: {DOMAIN}")

        # Check if the entity_id is valid
        entity_id = call.data.get(ATTR_ENTITY_ID)
        entity: ImageEntity | None = None
        for platform in platforms:
            entity_tmp: ImageEntity | None = platform.entities.get(entity_id, None)
            if entity_tmp is not None:
                entity = entity_tmp
                break
        if not entity:
            raise HomeAssistantError(
                f"Could not find entity {entity_id} from integration {DOMAIN}"
            )

        # Check write access to the file path
        filepath = Path(
            hass.config.path(
                call.data.get(
                    ATTR_SAVE2FILE,
                    "www/{filename}".format(
                        filename=entity.state_attributes.get("serial", DOMAIN),
                    ),
                )
            )
        )
        if not hass.config.is_allowed_path(str(filepath)):
            raise HomeAssistantError(
                """Cannot write `{path}`, no access to path;
                `allowlist_external_dirs` may need to be adjusted in `configuration.yaml`""".format(
                    path=str(filepath),
                )
            )
        else:
            filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write the image to the file
        image = await entity.async_image()
        try:
            if filepath.suffix != ".png":
                filepath = filepath.with_suffix(".png")

            await asyncio.to_thread(Path(filepath).write_bytes, image)
            hass.bus.fire(f"{domain}_image_saved", {"filename": filepath.name})
        except OSError as e:
            _LOGGER.error("Failed to save image due to file error: %s", e)

    async def simulating_earthquake(call: ServiceCall):
        """Simulate an earthquake."""
        data = call.data.get(ATTR_DATA, "")
        coordinator.simulating_notification = data

        if data == "":
            _LOGGER.warning("Abort earthquake simulation")
            return

        _LOGGER.warning("Start earthquake simulation")
        hass.bus.fire(
            f"{domain}_notification", {"earthquake": data}, origin=EventOrigin.local
        )

    hass.services.async_register(domain, "save2file", save_image)
    hass.services.async_register(domain, "simulator", simulating_earthquake)
