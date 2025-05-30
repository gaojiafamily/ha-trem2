"""Report refresh button for TREM2 component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON_ICON, DOMAIN, MANUFACTURER, __version__

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

BUTTON_ENTITYS = [
    ButtonEntityDescription(
        entity_category=EntityCategory.CONFIG,
        key="refresh_report",
        icon=BUTTON_ICON,
    ),
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Trem2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TREM refresh button from config."""
    # Create the sensor entity
    entities = []
    for entity in BUTTON_ENTITYS:
        if entity.key == "refresh_report":
            select_entity = RefreshButton(config_entry, entity)
            entities.append(select_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = select_entity

    async_add_entities(entities, update_before_add=True)


class RefreshButton(ButtonEntity):
    """Defines a report selects entity."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the Select."""
        self._attr_device_info = DeviceInfo(
            identifiers={(config_entry.domain, config_entry.entry_id)},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self.config_entry = config_entry
        self.coordinator = config_entry.runtime_data.coordinator
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.store.fetch_report()

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.config_entry.domain.upper()} {self.entity_description.key.replace('_', ' ').capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        device_info = self._attr_device_info
        if device_info:
            identifiers: set[tuple[str, str]] = device_info.get("identifiers", set())
            domain, suffix = next(iter(identifiers))
        else:
            domain = self.config_entry.domain
            suffix = "user"
        return f"{domain.lower()}_{suffix.lower()}_{self.entity_description.key.lower()}"
