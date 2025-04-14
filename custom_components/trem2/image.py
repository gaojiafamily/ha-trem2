"""Initialize the ImageEntity for TREM2 component."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from io import BytesIO
import logging
import re
from typing import Any

from pyvips import Image

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
    OFFICIAL_URL,
    TREM2_COORDINATOR,
    TREM2_NAME,
    __version__,
)
from .core.earthquake import get_calculate_intensity, intensity_to_text, round_intensity
from .core.map import draw as draw_isoseismal_map
from .update_coordinator import trem2_update_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: Callable,
) -> None:
    """Set up the image entity from a config entry."""
    domain_data: dict = hass.data[DOMAIN][config_entry.entry_id]
    name: str = domain_data[TREM2_NAME]
    coordinator: trem2_update_coordinator = domain_data[TREM2_COORDINATOR]

    # Create the image entity
    device = monitoring_image(hass, name, config_entry, coordinator)
    async_add_devices([device], update_before_add=True)


class monitoring_image(ImageEntity):
    """Representation of an image entity for displaying a custom SVG image as PNG."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        config_entry: ConfigEntry,
        coordinator: trem2_update_coordinator,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)

        self._coordinator = coordinator
        self._hass = hass

        attr_name = f"{name} Monitoring"
        self._attr_name = attr_name
        self._attr_unique_id = re.sub(r"\s+|@", "_", attr_name.lower())
        self._attr_content_type: str = "image/png"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
            name="Monitoring",
        )
        self._attributes = {}
        self._attr_value = {}

        self._cached_report_id = None
        self._cached_image_id = None
        self._cached_image: BytesIO | None = None

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                lambda: self.hass.async_create_task(self._update_callback())
            )
        )

    async def async_image(self) -> bytes | None:
        """Draw the monitoring image."""
        return self._cached_image

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
        hass_config = self.hass.config

        # Get the latest notification data
        eq_data = await self.get_eew_data()
        report_data = await self.get_report_data()

        # Check _cached_image_id to avoid unnecessary updates
        eq_id = "-".join(
            map(
                str,
                (
                    eq_data.get("id", "XXXXXXX"),
                    eq_data.get("serial", "X"),
                ),
            )
        )
        report_id = report_data.get("id", "")
        if eq_id == self._cached_image_id and report_id == self._cached_report_id:
            return

        # Calculate the intensity
        intensitys = get_calculate_intensity(
            eq_data.get(
                "eq",
                await self.get_int_data(),
            )
        )

        # Write the attributes with the intensity values greater than 0
        self._attr_value = {
            ATTR_COUNTY.get(k, k): intensity_to_text(v)
            for k, v in intensitys.items()
            if round_intensity(v) > 0
        }

        assets_path = f"custom_components/{DOMAIN}/assets"
        eew_time = eq_data.get("time", 0)
        report_time = report_data.get("time", 0)
        if report_time < eew_time:
            bg_path = hass_config.path(f"{assets_path}/brand.svg")
            url = OFFICIAL_URL
        else:
            bg_path = hass_config.path(f"{assets_path}/cwa_logo.svg")

            if self.report_invalid(report_time, eew_time):
                url = "https://cwa.gov.tw/v8/c/e/index.html"
            else:
                url = f"https://cwa.gov.tw/v8/c/e/eq/eq{report_id}.html"

        # Draw the isoseismal map
        svg_cont = draw_isoseismal_map(
            intensitys,
            eq_data,
            eq_id,
            bg_path,
            url,
        )

        # Remove BOM and decode the SVG data
        svg_byte = svg_cont.lstrip().encode("utf-8").lstrip(b"\xef\xbb\xbf")

        # Convert the SVG data to PNG using pyvips
        svg_data: Image = await asyncio.to_thread(Image.new_from_buffer, svg_byte, "")
        output = await asyncio.to_thread(svg_data.write_to_buffer, ".png")

        # Store the PNG data in the _cached_image
        self._cached_image = output
        self._attr_image_last_updated = dt_util.utcnow()

        # Update the _cached_image_id
        self._cached_report_id = report_id
        self._cached_image_id = eq_id
        self._attr_value[ATTR_ID] = eq_id

        # Update the attributes
        self.async_write_ha_state()

    def report_invalid(self, t1, t2, threshold_seconds=6000):
        """Check if the report time is valid."""
        t1_sec = t1 // 1000
        t2_sec = t2 // 1000

        delta = abs(t1_sec - t2_sec)
        return delta > threshold_seconds

    async def get_eew_data(self) -> dict:
        """Get the latest notification data."""
        if len(self._coordinator.earthquake_notification) > 0:
            return self._coordinator.earthquake_notification[0]

        return {}

    async def get_report_data(self) -> dict:
        """Get the latest report data."""
        return self._coordinator.report_data

    async def get_int_data(self) -> dict:
        """Get the latest intensity data."""
        return self._coordinator.intensity
