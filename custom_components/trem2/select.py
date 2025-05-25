"""Report selects for TREM2 component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    REPORT_ICON,
    MANUFACTURER,
    __version__,
)

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

SELECT_ENTITYS = [
    SelectEntityDescription(
        key="report",
        icon=REPORT_ICON,
    ),
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Trem2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TREM select from config."""
    # Create the sensor entity
    entities = []
    for entity in SELECT_ENTITYS:
        if entity.key == "report":
            select_entity = ReportSelect(config_entry, entity)
            entities.append(select_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = select_entity

    async_add_entities(entities, update_before_add=True)


class ReportSelect(SelectEntity):
    """Defines a report selects entity."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize the Select."""
        self._attr_device_info = DeviceInfo(
            identifiers={(config_entry.domain, config_entry.options.get(CONF_EMAIL, "user"))},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self.config_entry = config_entry
        self.coordinator = config_entry.runtime_data.coordinator
        self.entity_description = description

        self._attr_current_option = None

    @property
    def options(self):
        """Return options to selects."""
        return self._get_options()

    def _get_options(self):
        """Generate options from runtime data."""
        data = self.coordinator.data or {}
        report = data.get("report") or {}
        cache = report.get("cache") or []

        return [v["id"] for v in cache]

    async def async_select_index(self, idx: int) -> None:
        """Select new option by index."""
        options = self._get_options()

        new_index = idx % len(options)
        await self.async_select_option(options[new_index])

    async def async_offset_index(self, offset: int, cycle: bool) -> None:
        """Offset current index."""
        if self._attr_current_option is None:
            return

        options = self._get_options()
        current_index = options.index(self._attr_current_option)
        new_index = current_index + offset
        if cycle:
            new_index = new_index % len(options)
        elif new_index < 0:
            new_index = 0
        elif new_index >= len(options):
            new_index = len(options) - 1

        if cycle or current_index != new_index:
            await self.async_select_option(options[new_index])

    async def async_first(self) -> None:
        """Select first option."""
        await self.async_select_index(0)

    async def async_last(self) -> None:
        """Select last option."""
        await self.async_select_index(-1)

    async def async_next(self, cycle: bool) -> None:
        """Select next option."""
        await self.async_offset_index(1, cycle)

    async def async_previous(self, cycle: bool) -> None:
        """Select previous option."""
        await self.async_offset_index(-1, cycle)

    async def async_select_option(self, option: str):
        """Change the selected option."""
        if not self.available:
            raise HomeAssistantError("Entity unavailable")

        options = self._get_options()

        match option:
            case value if value is None or value not in options:
                raise HomeAssistantError(
                    f"Invalid option for {self.entity_description.name} {option}. Valid options: {options}"
                )
            case _:
                self._attr_current_option = option
                self.config_entry.runtime_data.selected_option = option

        self.coordinator.async_update_listeners()
        self.async_write_ha_state()

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.config_entry.domain.upper()} {self.entity_description.key.capitalize()}"

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
