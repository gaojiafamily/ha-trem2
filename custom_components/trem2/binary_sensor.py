"""Sensor for the Taiwan Real-time Earthquake Monitoring."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform

from .const import (
    ATTR_AUTHOR,
    ATTR_ID,
    ATTR_LIST,
    ATTR_API_NODE,
    DOMAIN,
    INT_DEFAULT_ICON,
    INT_TRIGGER_ICON,
    MANUFACTURER,
    UPDATE_COORDINATOR,
    ZIP3_TOWN,
    __version__,
)
from .update_coordinator import Trem2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)


SENSOR_ENTITYS = [
    BinarySensorEntityDescription(
        key="intensity",
        icon=INT_DEFAULT_ICON,
        device_class=BinarySensorDeviceClass.VIBRATION,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TREM binary sensor from config."""
    domain_data: dict = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: Trem2UpdateCoordinator = domain_data[UPDATE_COORDINATOR]

    # Create the binary sensor entity
    entities = []
    for entity in SENSOR_ENTITYS:
        if entity.key == "intensity":
            entities.append(IntensityBinarySensor(config_entry, coordinator, entity, hass))
    async_add_entities(entities, update_before_add=True)

    # Register services for the binary sensor
    platform = async_get_current_platform()
    key = f"{DOMAIN}_set_ws_node_registered"
    if not hass.data[DOMAIN].get(key):
        platform.async_register_entity_service(
            "set_ws_node",
            {
                vol.Optional(ATTR_API_NODE): str,
                vol.Optional(CONF_URL): str,
            },
            "async_handle_set_ws_node",
        )
        hass.data[DOMAIN][key] = True


class IntensityBinarySensor(BinarySensorEntity):
    """Defines a rts sensor entity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: Trem2UpdateCoordinator,
        description: BinarySensorEntityDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the binary sensor."""
        self._coordinator = coordinator
        self._hass = hass

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.options.get(CONF_EMAIL, "user"))},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self.entity_description = description

        self._attr_value = {}
        self._state = False
        self._icon = INT_DEFAULT_ICON

    async def async_update(self):
        """Schedule a custom update via the common entity update service."""
        if "area" in self._coordinator.state.intensity:
            self._icon = INT_TRIGGER_ICON
        else:
            self._icon = INT_DEFAULT_ICON

        self._state = "area" in self._coordinator.state.intensity
        self._attr_value = self.convert_zip3_town()

        return self

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._update_callback,
            )
        )

    def convert_zip3_town(self) -> dict:
        """Convert ZIP Code to Township name."""
        if "area" in self._coordinator.state.intensity:
            area = {}
            for i, j in self._coordinator.state.intensity["area"]:
                town = []
                for zipcode in j:
                    if zipcode in ZIP3_TOWN:
                        town.extend(ZIP3_TOWN[zipcode])
                area[i] = town

            return {
                ATTR_ID: "-".join(
                    [
                        str(self._coordinator.state.intensity.get("id") or ""),
                        str(self._coordinator.state.intensity.get("serial") or ""),
                    ]
                ),
                ATTR_AUTHOR: self._coordinator.state.intensity["author"],
                ATTR_LIST: area,
            }

        return {}

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return f"{DOMAIN.upper()} {self.entity_description.key.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id of the binary sensor."""
        device_info = self._attr_device_info
        if device_info:
            identifiers: set[tuple[str, str]] = device_info.get("identifiers", set())
            domain, suffix = next(iter(identifiers))
        else:
            domain = DOMAIN
            suffix = "user"
        return f"{domain.lower()}_{suffix.lower()}_{self.entity_description.key.lower()}"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self._attr_value

    @callback
    def _update_callback(self) -> None:
        """Handle updated data from the coordinator."""
        if not self._coordinator.last_update_success:
            return

        self.async_write_ha_state()

    async def async_handle_set_ws_node(self, **kwargs):
        """Set the node specified by the user."""
        api_node = kwargs.get(ATTR_API_NODE)
        base_url = kwargs.get(CONF_URL)

        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        if not self._coordinator.ws_client.state.conn:
            raise HomeAssistantError("WebSocket is unavailable.")

        self._coordinator.ws_client.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        self._coordinator.update_interval = self._coordinator.conf.fast_interval
        await self._coordinator.async_refresh()

        self._coordinator.server_status_event(node=api_node)
