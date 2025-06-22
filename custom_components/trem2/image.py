"""Initialize the ImageEntity for TREM2 component."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyvips import Image
import voluptuous as vol

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_EMAIL, CONF_FILENAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from homeassistant.util import dt as dt_util

from .const import ATTR_COUNTY, ATTR_ID, ATTRIBUTION, DOMAIN, MANUFACTURER, OFFICIAL_URL, __version__
from .core.earthquake import get_calculate_intensity, intensity_to_text, round_intensity
from .core.map import draw as draw_isoseismal_map
from .runtime import Trem2ImageData

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

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
    entities = []
    for entity in IMAGE_ENTITYS:
        if entity.key == "monitoring":
            image_entity = MonitoringImage(
                config_entry,
                entity,
                hass,
            )
            entities.append(image_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = image_entity

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
            identifiers={(config_entry.domain, config_entry.entry_id)},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )

        self.config_entry = config_entry
        self.coordinator = config_entry.runtime_data.coordinator
        self.data = Trem2ImageData()
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        await super().async_added_to_hass()

        def _schedule_update_callback() -> None:
            self.hass.async_create_task(self._update_callback())

        self.async_on_remove(
            self.coordinator.async_add_listener(
                _schedule_update_callback,
            )
        )

    async def async_will_remove_from_hass(self):
        """Unload when this Entity has been remove from HA."""
        await super().async_will_remove_from_hass()

    async def async_image(self) -> bytes | None:
        """Draw the monitoring image."""
        return self.data.image

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

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
        self.data.attributes = {}
        for k, v in self.data.attr_value.items():
            self.data.attributes[k] = v

        return self.data.attributes

    async def _update_callback(self):
        """Handle updated data from the coordinator."""
        if not self.coordinator.last_update_success:
            return

        try:
            # Get the latest earthquake data
            report_id = getattr(self.config_entry.runtime_data, "selected_option", None)
            eew = await self.coordinator.data_client.load_eew_data(report_id)

            # Check state change
            if self.data.image_id == eew.get("id"):
                return

            # Calculate the intensity
            match eew:
                case {"intensity": intensitys}:
                    self.data.intensitys = intensitys
                    self.data.attr_value = eew["list"]

                case {"eq": eq_info}:
                    self.data.intensitys = get_calculate_intensity(eq_info)
                    self.data.attr_value = {
                        ATTR_COUNTY.get(k, k): intensity_to_text(v)
                        for k, v in self.data.intensitys.items()
                        if round_intensity(v) > 0
                    }

            # Draw map
            await self._drawing_map(
                eew,
                eew.get("id", self.data.image_id),
            )
        except TypeError as ex:
            _LOGGER.error("TypeError occurred while processing earthquake data: %s", ex)
        except AttributeError as ex:
            _LOGGER.error(
                "AttributeError occurred while accessing earthquake data: %s",
                ex,
                exc_info=ex,
            )

        # Update the attributes
        self.async_write_ha_state()

    async def _drawing_map(self, eew, eq_id):
        """Draw Monitoring Image."""
        assets_path = f"custom_components/{DOMAIN}/assets"

        # QR Code data
        bg_path = self.hass.config.path(f"{assets_path}/brand.svg")
        url = OFFICIAL_URL
        if "md5" in eew:
            bg_path = self.hass.config.path(f"{assets_path}/cwa_logo.svg")
            url = f"https://www.cwa.gov.tw/V8/C/E/EQ/EQ{eq_id}.html"

        # Draw the isoseismal map
        svg_cont = draw_isoseismal_map(
            self.data.intensitys,
            eew,
            eq_id,
            bg_path,
            url,
        )

        # Remove BOM and decode the SVG data
        svg_byte = svg_cont.lstrip().encode("utf-8").lstrip(b"\xef\xbb\xbf")

        # Convert the SVG bytes to PNG using pyvips
        svg_data: Image = await asyncio.to_thread(  # type: ignore  # noqa: PGH003
            Image.new_from_buffer,
            svg_byte,
            "",
        )

        # Storing the PNG to image
        self.data.image = await asyncio.to_thread(  # type: ignore  # noqa: PGH003
            svg_data.write_to_buffer,
            ".png",
        )
        self._attr_image_last_updated = dt_util.utcnow()

        # Update the _image_id
        self.data.image_id = eq_id
        self.data.attr_value[ATTR_ID] = eq_id

    async def async_handle_save_image(self, **kwargs) -> None:
        """Handle the save image service."""
        extra_state_attr = self.data.attributes

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
