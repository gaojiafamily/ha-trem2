"""Custom Image Display for Home Assistant."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import logging
import re
from typing import Any

from cairosvg import svg2png

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COUNTY,
    ATTR_ID,
    ATTRIBUTION,
    DOMAIN,
    MANUFACTURER,
    TREM2_COORDINATOR,
    TREM2_NAME,
    __version__,
)
from .core.earthquake import get_calculate_intensity, intensity_to_text, round_intensity
from .core.map import draw as draw_isoseismal_map
from .update_coordinator import trem2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: Callable,
) -> None:
    """Set up the image entity from a config entry."""

    domain_data: dict = hass.data[DOMAIN][config_entry.entry_id]
    name: str = domain_data[TREM2_NAME]
    coordinator: trem2UpdateCoordinator = domain_data[TREM2_COORDINATOR]

    # Create the image entity
    device = earthquakeImage(hass, name, config_entry, coordinator)
    async_add_devices([device], update_before_add=True)


class earthquakeImage(ImageEntity):
    """Representation of an image entity for displaying a custom SVG image as PNG."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        config_entry: ConfigEntry,
        coordinator: trem2UpdateCoordinator,
    ) -> None:
        """Initialize the image entity."""

        super().__init__(hass)

        self._coordinator = coordinator
        self._hass = hass

        attr_name = f"{name} Isoseismal Map"
        self._attr_name = attr_name
        self._attr_unique_id = re.sub(r"\s+|@", "_", attr_name.lower())
        self._attr_content_type: str = "image/png"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
            name="Isoseismal Map",
        )
        self._attributes = {}
        self._attr_value = {}

        self._last_draw_id = None
        self._last_draw: BytesIO | None = None

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""

        self.async_on_remove(
            self._coordinator.async_add_listener(
                lambda: self.hass.async_create_task(self._update_callback())
            )
        )

    async def async_image(self) -> bytes | None:
        """Draw the isoseismal map."""

        return self._last_draw

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""

        self._attributes = {}
        self._attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        for k, v in self._attr_value.items():
            self._attributes[k] = v

        return self._attributes

    async def _update_callback(self):
        """Handle updated data from the coordinator."""

        # Get the latest earthquake data
        earthquake = await self.get_eew_data()
        earthquake_id = []
        earthquake_id.append(str(earthquake.get("id", "xxxxxx")))
        earthquake_id.append(str(earthquake.get("serial", "x")))

        # Check last_draw_id to avoid unnecessary updates
        curr_draw_id = "-".join(earthquake_id)
        if curr_draw_id == self._last_draw_id:
            return

        # Calculate the intensity
        intensitys = get_calculate_intensity(earthquake.get("eq", {}))

        # Write the attributes with the intensity values greater than 0
        self._attr_value = {
            ATTR_COUNTY.get(k, k): intensity_to_text(v)
            for k, v in intensitys.items()
            if round_intensity(v) > 0
        }

        # Create a BytesIO object to store the PNG data
        if curr_draw_id == "xxxxxx-x":
            url = "https://www.gj-smart.com"
            relative_path = f"custom_components/{DOMAIN}/assets/brand.svg"
        else:
            url = None
            relative_path = f"custom_components/{DOMAIN}/assets/CWA_Logo.svg"

        bg_path = self.hass.config.path(relative_path)
        bytestring = draw_isoseismal_map(earthquake, intensitys, bg_path, url)
        output = BytesIO()

        # Convert SVG to PNG
        svg2png(
            bytestring=bytestring,
            write_to=output,
            output_width=1000,
            output_height=1000,
        )
        self._last_draw = output.getvalue()
        self._attr_image_last_updated = dt_util.utcnow()

        # Update the last_draw_id
        self._last_draw_id = curr_draw_id
        self._attr_value[ATTR_ID] = curr_draw_id

        # Update the attributes
        self.async_write_ha_state()

    async def get_eew_data(self) -> dict:
        """Get the latest earthquake data."""

        if len(self._coordinator.earthquakeData) > 0:
            return self._coordinator.earthquakeData[0]

        return []
