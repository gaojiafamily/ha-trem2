"""Initialize the ImageEntity for TREM2 component."""

from __future__ import annotations

import asyncio
import dataclasses
from io import BytesIO
import logging
import re
from typing import Any

from pyvips import Image

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COUNTY,
    ATTR_ID,
    ATTR_REPORT_IMG_URL,
    ATTRIBUTION,
    DOMAIN,
    MANUFACTURER,
    OFFICIAL_URL,
    REPORT_IMG_URL,
    UPDATE_COORDINATOR,
    __version__,
)
from .core.earthquake import get_calculate_intensity, intensity_to_text, round_intensity
from .core.map import draw as draw_isoseismal_map
from .update_coordinator import Trem2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)

IMAGE_ENTITYS = [
    ImageEntityDescription(key="monitoring"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the image entity from a config entry."""
    domain_data: dict = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: Trem2UpdateCoordinator = domain_data[UPDATE_COORDINATOR]

    # Create the image entity
    entities = []
    for entity in IMAGE_ENTITYS:
        if entity.key == "monitoring":
            entities.append(MonitoringImage(config_entry, coordinator, entity, hass))
    async_add_entities(entities, update_before_add=True)


@dataclasses.dataclass
class ImageStore:
    """Manage Image data."""

    cached_image_id = None
    cached_image: BytesIO | None = None
    attributes = {}
    attr_value = {}


class MonitoringImage(ImageEntity):
    """Representation of an image entity for displaying a custom SVG image as PNG."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: Trem2UpdateCoordinator,
        description: ImageEntityDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)

        self._coordinator = coordinator
        self._hass = hass

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.options.get(CONF_EMAIL, "user"))},
            name=config_entry.options.get(CONF_EMAIL, "user"),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self.entity_description = description

        self.image_store = ImageStore()

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                lambda: self.hass.async_create_task(
                    self._update_callback(),
                )
            )
        )

    async def async_image(self) -> bytes | None:
        """Draw the monitoring image."""
        return self.image_store.cached_image

    def image(self) -> bytes | None:
        """Draw the monitoring image."""
        return self.image_store.cached_image

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def content_type(self):
        """Return the content type of the image."""
        return "image/png"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DOMAIN.upper()} {self.entity_description.key.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        domain, email = next(iter(self._attr_device_info["identifiers"]))
        return f"{domain.lower()}_{email.lower()}_{self.entity_description.key.lower()}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        self.image_store.attributes = {}
        self.image_store.attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        for k, v in self.image_store.attr_value.items():
            self.image_store.attributes[k] = v

        return self.image_store.attributes

    async def _update_callback(self):
        """Handle updated data from the coordinator."""
        if not self._coordinator.last_update_success:
            return

        # Get the latest notification data
        try:
            eq_data = await self.get_eew_data()
            eew_id = eq_data.get("id", None)
            if eew_id is None:
                return

            if "serial" in eq_data:
                eq_id = "-".join(
                    map(
                        str,
                        (
                            eew_id,
                            eq_data.get("serial", ""),
                        ),
                    )
                )
            else:
                pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
                match = re.search(
                    pattern,
                    eew_id,
                )
                eq_id = "-".join(match.groups())

            # Check state change
            if self.image_store.cached_image_id == eq_id:
                return

            # Calculate the intensity
            if "list" in eq_data:
                intensitys = await self.get_int_data(eq_data["list"])
                self.image_store.attr_value = {
                    ATTR_REPORT_IMG_URL: f"{REPORT_IMG_URL}/{eew_id}.jpg",
                }
            else:
                intensitys = (
                    get_calculate_intensity(
                        eq_data.get(
                            "eq",
                            None,
                        )
                    )
                    or await self.get_int_data()
                )

                # Write the attributes with the intensity values greater than 0
                self.image_store.attr_value = {
                    ATTR_COUNTY.get(k, k): intensity_to_text(
                        v,
                    )
                    for k, v in intensitys.items()
                    if round_intensity(v) > 0
                }

            # QR Code data
            assets_path = f"custom_components/{DOMAIN}/assets"
            bg_path = self.hass.config.path(f"{assets_path}/brand.svg")
            url = OFFICIAL_URL
            if "md5" in eq_data:
                bg_path = self.hass.config.path(f"{assets_path}/cwa_logo.svg")
                url = f"https://www.cwa.gov.tw/V8/C/E/EQ/EQ{eq_id}.html"

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
            self.image_store.cached_image = output
            self._attr_image_last_updated = dt_util.utcnow()

            # Update the _cached_image_id
            self.image_store.cached_image_id = eq_id
            self.image_store.attr_value[ATTR_ID] = eq_id
        except TypeError as ex:
            _LOGGER.error("TypeError occurred while processing earthquake data: %s", ex)
        except AttributeError as ex:
            _LOGGER.error(
                "AttributeError occurred while accessing earthquake data: %s",
                str(ex),
                exc_info=ex,
            )

        # Update the attributes
        self.async_write_ha_state()

    async def get_eew_data(self) -> dict:
        """Get the report or latest notification data."""
        fetch_eew = self._coordinator.state.earthquake
        fetch_report = self._coordinator.state.report

        # Get the latest earthquake data
        if isinstance(fetch_eew, list) and len(fetch_eew) > 0:
            eew_data = fetch_eew[0]
        else:
            eew_data = fetch_eew or {}

        # Get the latest report data
        if isinstance(fetch_report, list) and len(fetch_report) > 0:
            report_data = fetch_report[0]
        else:
            report_data = fetch_report or {}

        # Check if the report data is more recent than the notification data
        if report_data.get("time", 0) > eew_data.get("time", 0):
            eew_data["id"] = report_data.get("id", None)
            eew_data.pop("serial", None)
            eq: dict = eew_data.get("eq", {})
            for key in ("lat", "lon", "depth", "loc", "mag", "time"):
                eq[key] = report_data.get(key, None)
            eq["max"] = report_data.get("int", None)
            eew_data["eq"] = eq
            eew_data["list"] = report_data.get("list", {})
            eew_data["md5"] = report_data.get("md5", None)

        # Otherwise, return the notification data
        return eew_data

    async def get_int_data(self, intensitys: dict | None = None) -> dict:
        """Get the latest intensity data."""
        int_list = {}

        if intensitys is None:
            int_list = self._coordinator.state.intensity
        else:
            county_list = {v: k for k, v in ATTR_COUNTY.items()}
            for county, detail in intensitys.items():
                int_list[county_list[county]] = detail["int"]

        return int_list
