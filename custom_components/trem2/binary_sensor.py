"""Sensor for the Taiwan Real-time Earthquake Monitoring."""

from __future__ import annotations

from datetime import datetime
import logging
from math import ceil
from typing import TYPE_CHECKING, Any

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
    ATTR_API_NODE,
    ATTR_AUTHOR,
    ATTR_ID,
    ATTR_LIST,
    DOMAIN,
    INT_DEFAULT_ICON,
    INT_TRIGGER_ICON,
    MANUFACTURER,
    __version__,
)

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData


_LOGGER = logging.getLogger(__name__)


SENSOR_ENTITYS = [
    BinarySensorEntityDescription(
        key="intensity",
        icon=INT_DEFAULT_ICON,
        device_class=BinarySensorDeviceClass.VIBRATION,
    ),
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Trem2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TREM binary sensor from config."""
    # Create the binary sensor entity
    entities = []
    for entity in SENSOR_ENTITYS:
        if entity.key == "intensity":
            sensor_entity = IntensityBinarySensor(
                config_entry,
                entity,
            )
            entities.append(sensor_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = sensor_entity

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
        config_entry: Trem2ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self.coordinator = config_entry.runtime_data.coordinator
        self.entity_description = description

        self._attr_value = {}
        self._state = False
        self._icon = INT_DEFAULT_ICON

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self._update_callback,
            )
        )

    async def async_will_remove_from_hass(self):
        """Unload when this Entity has been remove from HA."""
        await super().async_will_remove_from_hass()

    async def async_update(self):
        """Perform update data."""
        if not self.coordinator.last_update_success:
            return

        if self.coordinator.data:
            intensity_data: dict = self.coordinator.data["recent"]["intensity"]
            intensity_time = int(intensity_data.get("id", 0))
            dt = datetime.now()
            current_time = dt.timestamp() * 1000
            diff_time = ceil(abs(current_time - intensity_time) / 1000)

            # Update state
            if "area" in intensity_data and diff_time < 300:
                self._icon = INT_TRIGGER_ICON
                self._state = True
            else:
                self._icon = INT_DEFAULT_ICON
                self._state = False

            # Update attributes
            _, lists = await self.coordinator.store.load_intensitys()
            if lists:
                self._attr_value = {
                    ATTR_ID: "-".join(
                        [
                            str(intensity_data.get("id") or ""),
                            str(intensity_data.get("serial") or ""),
                        ]
                    ),
                    ATTR_AUTHOR: intensity_data["author"],
                    ATTR_LIST: lists,
                }

            self.async_write_ha_state()

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

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
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_handle_set_ws_node(self, **kwargs):
        """Set the node specified by the user."""
        api_node = kwargs.get(ATTR_API_NODE)
        base_url = kwargs.get(CONF_URL)

        if api_node is None and base_url is None:
            raise ServiceValidationError("Missing `Server URL` or `ExpTech Node`")

        if not self.coordinator.client.websocket.state.conn:
            raise HomeAssistantError("WebSocket is unavailable.")

        api_node, base_url = self.coordinator.client.websocket.initialize_route(
            action="service",
            api_node=api_node,
            base_url=base_url,
        )
        self.coordinator.update_interval = self.coordinator.conf.fast_interval
        await self.coordinator.async_refresh()

        await self.coordinator.server_status_event(node=api_node)
