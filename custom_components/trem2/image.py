"""Initialize the ImageEntity for TREM2 component."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from pathlib import Path
import re
from typing import Any, TYPE_CHECKING
import voluptuous as vol

from pyvips import Image

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_EMAIL, CONF_FILENAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
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
    __version__,
)
from .core.earthquake import get_calculate_intensity, intensity_to_text, round_intensity
from .core.map import draw as draw_isoseismal_map

if TYPE_CHECKING:
    from .data_classes import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

IMAGE_ENTITYS = [
    ImageEntityDescription(key="monitoring"),
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Trem2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the image entity from a config entry."""
    # Create the image entity
    entities = []
    for entity in IMAGE_ENTITYS:
        if entity.key == "monitoring":
            entities.append(
                MonitoringImage(
                    config_entry,
                    entity,
                    hass,
                )
            )
    async_add_entities(entities, update_before_add=True)

    # Register services for the binary sensor
    platform = async_get_current_platform()
    key = f"{config_entry.domain}_save2file_registered"
    if not hass.data[config_entry.domain].get(key):
        platform.async_register_entity_service(
            "save2file",
            {
                vol.Optional(CONF_FILENAME): str,
            },
            "async_handle_save_image",
        )
        hass.data[config_entry.domain][key] = True


@dataclasses.dataclass
class ImageStore:
    """Manage Image data."""

    cached_image_id: str | None = None
    cached_image: bytes | None = None
    attributes = {}
    attr_value = {}
    intensitys = {}


class MonitoringImage(ImageEntity):
    """Representation of an image entity for displaying a custom SVG image as PNG."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        description: ImageEntityDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)

        self._attr_device_info = DeviceInfo(
            identifiers={(config_entry.domain, config_entry.options.get(CONF_EMAIL, "user"))},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )

        self.config_entry = config_entry
        self.entity_description = description
        self.image_store = ImageStore()

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""

        def _schedule_update_callback() -> None:
            self.hass.async_create_task(self._update_callback())

        self.async_on_remove(
            self.config_entry.runtime_data.coordinator.async_add_listener(
                _schedule_update_callback,
            )
        )

    async def async_image(self) -> bytes | None:
        """Draw the monitoring image."""
        return self.image_store.cached_image

    @property
    def available(self):
        """Return True if entity is available."""
        return self.config_entry.runtime_data.coordinator.last_update_success

    @property
    def content_type(self):
        """Return the content type of the image."""
        return "image/png"

    @property
    def name(self):
        """Return the name of the image."""
        return f"{self.config_entry.domain.upper()} {self.entity_description.key.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id of the image."""
        device_info = self._attr_device_info
        if device_info:
            identifiers: set[tuple[str, str]] = device_info.get("identifiers", set())
            domain, suffix = next(iter(identifiers))
        else:
            domain = DOMAIN
            suffix = "user"
        return f"{domain.lower()}_{suffix.lower()}_{self.entity_description.key.lower()}"

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
        if not self.config_entry.runtime_data.coordinator.last_update_success:
            return

        # Get the latest earthquake data
        eq_data = await self.get_eew_data()
        if "id" in eq_data:
            eq_id = "-".join(
                [
                    str(eq_data["id"]),
                    str(eq_data.get("serial", "")),
                ]
            )
        else:
            return

        # Get the latest notification data
        try:
            if "serial" not in eq_data:
                pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
                match = re.search(
                    pattern,
                    eq_data["id"],
                )
                if match:
                    eq_id = "-".join(match.groups())

            # Check state change
            if self.image_store.cached_image_id == eq_id:
                return

            # Calculate the intensity
            match eq_data:
                case {"list": list_data}:
                    self.image_store.intensitys = await self.get_int_data(list_data)
                    self.image_store.attr_value = {
                        ATTR_REPORT_IMG_URL: f"{REPORT_IMG_URL}/{eq_data['id']}.jpg",
                    }
                case {"eq": eq_info}:
                    self.image_store.intensitys = get_calculate_intensity(
                        eq_info or await self.get_int_data(),
                    )
                    self.image_store.attr_value = {
                        ATTR_COUNTY.get(k, k): intensity_to_text(v)
                        for k, v in self.image_store.intensitys.items()
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
                self.image_store.intensitys,
                eq_data,
                eq_id,
                bg_path,
                url,
            )

            # Remove BOM and decode the SVG data
            svg_byte = svg_cont.lstrip().encode("utf-8").lstrip(b"\xef\xbb\xbf")

            # Convert the SVG bytes to PNG using pyvips
            svg_data: Image = await asyncio.to_thread(  # type: ignore
                Image.new_from_buffer,
                svg_byte,
                "",
            )

            # Storing the PNG to cached_image
            self.image_store.cached_image = await asyncio.to_thread(  # type: ignore
                svg_data.write_to_buffer,
                ".png",
            )
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
        fetch_eew = self.config_entry.runtime_data.coordinator.state.earthquake
        fetch_report = self.config_entry.runtime_data.coordinator.state.report

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
            for key in ("author", "lat", "lon", "depth", "loc", "mag", "time"):
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
            int_list = self.config_entry.runtime_data.coordinator.state.intensity
        else:
            county_list = {v: k for k, v in ATTR_COUNTY.items()}
            for county, detail in intensitys.items():
                int_list[county_list[county]] = detail["int"]

        return int_list

    async def async_handle_save_image(self, **kwargs) -> None:
        """Handle the save image service."""
        extra_state_attr = self.image_store.attributes

        try:
            defult_filename = (
                f"{DOMAIN}_{self.entity_description.key}_{extra_state_attr['serial']}"
                if "serial" in extra_state_attr
                else DOMAIN
            )
            filepath = Path(
                self.hass.config.path(
                    kwargs.get(
                        CONF_FILENAME,
                        f"www/{defult_filename}",
                    )
                )
            )

            if filepath.suffix != ".png":
                filepath = filepath.with_suffix(".png")

            filepath.parent.mkdir(parents=True, exist_ok=True)
            if not self.hass.config.is_allowed_path(str(filepath)):
                raise HomeAssistantError(
                    f"Cannot write `{filepath!s}`, no access to path; "
                    "`allowlist_external_dirs` may need to be adjusted in `configuration.yaml`"
                )

            image = await self.async_image()
            if isinstance(image, bytes):
                await asyncio.to_thread(filepath.write_bytes, image)
            else:
                raise HomeAssistantError(f"Image is not bytes: {image}")
        except OSError as e:
            raise HomeAssistantError(f"Failed to save image due to file error: {e}") from e

        self.hass.bus.fire(
            f"{DOMAIN}_image_saved",
            {
                "entity_id": self.entity_id,
                "filename": filepath.name,
                "folder": str(filepath.parent),
            },
        )
