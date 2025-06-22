"""Initialize the SensorEntity for TREM2 component."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_LATITUDE,
    ATTR_LOCATION,
    ATTR_LONGITUDE,
    CONF_EMAIL,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_AUTHOR,
    ATTR_DEPTH,
    ATTR_ID,
    ATTR_LIST,
    ATTR_MAG,
    ATTR_TIME,
    ATTRIBUTION,
    BASE_INTERVAL,
    DEFAULT_ICON,
    DOMAIN,
    MANUFACTURER,
    NOTIFICATION_ATTR,
    TZ_TW,
    TZ_UTC,
    __version__,
)

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)


SENSOR_ENTITYS = [
    SensorEntityDescription(
        key="notification",
        icon=DEFAULT_ICON,
    ),
    SensorEntityDescription(
        key="protocol",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Trem2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entity from a config entry."""
    entities = []
    for entity in SENSOR_ENTITYS:
        if entity.key == "notification":
            sensor_entity = NotificationSensor(config_entry, entity)
            entities.append(sensor_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = sensor_entity
        if entity.key == "protocol":
            sensor_entity = DiagnosticsSensor(config_entry, entity)
            entities.append(sensor_entity)
            hass.data[DOMAIN][config_entry.entry_id][entity.key] = sensor_entity

    async_add_entities(entities, update_before_add=True)


class NotificationSensor(SensorEntity):
    """Defines a earthquake sensor entity."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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

        self._attributes = {}
        self._attr_value = {}
        for k in NOTIFICATION_ATTR:
            self._attr_value[k] = ""
        self._state = ""
        self.coordinator.async_add_listener(self.async_write_ha_state)

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""

        def _schedule_update_callback() -> None:
            self.hass.async_create_task(self._update_callback())

        self.async_on_remove(
            self.coordinator.async_add_listener(
                _schedule_update_callback,
            )
        )

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

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        self._attributes = {}
        self._attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        for k, v in self._attr_value.items():
            self._attributes[k] = v

        return self._attributes

    async def _update_callback(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.last_update_success:
            return

        try:
            # Get the latest earthquake data
            report_id = getattr(self.config_entry.runtime_data, "selected_option", None)
            eew = await self.coordinator.data_client.load_eew_data(report_id)
            eq: dict = eew.get("eq", {})

            if self._state == eew.get("id"):
                return

            # formatted the time of occurrence
            if "time" in eq:
                time_of_occurrence = datetime.fromtimestamp(
                    round(eq["time"] / 1000),
                    TZ_UTC,
                ).astimezone(TZ_TW)
            else:
                time_of_occurrence = datetime.now()

            # Update the state
            self._attr_value[ATTR_AUTHOR] = eew.get("author", eq.get("author", ""))
            self._attr_value[ATTR_ID] = eew["id"]
            self._attr_value[ATTR_LOCATION] = eq.get("loc", "")
            self._attr_value[ATTR_LONGITUDE] = eq.get("lon", "")
            self._attr_value[ATTR_LATITUDE] = eq.get("lat", "")
            self._attr_value[ATTR_MAG] = eq.get("mag", "")
            self._attr_value[ATTR_DEPTH] = eq.get("depth", "")
            self._attr_value[ATTR_TIME] = time_of_occurrence.strftime("%Y/%m/%d %H:%M:%S")
            self._attr_value[ATTR_LIST] = eew.get("list")

            self._state = eew["id"]
        except TypeError as ex:
            _LOGGER.error("TypeError occurred while processing earthquake data: %s", ex)
        except AttributeError as ex:
            _LOGGER.error(
                "AttributeError occurred while accessing earthquake data: %s",
                ex,
                exc_info=ex,
            )

        self.async_write_ha_state()


class DiagnosticsSensor(SensorEntity):
    """Defines a diagnostics sensor entity."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(config_entry.domain, config_entry.entry_id)},
            name=config_entry.options.get(CONF_EMAIL, config_entry.title),
            manufacturer=MANUFACTURER,
            model="ExpTechTW TREM",
            sw_version=__version__,
        )
        self._attr_should_poll = True
        self.config_entry = config_entry
        self.coordinator = config_entry.runtime_data.coordinator
        self.entity_description = description

        self._state = ""
        self._attributes = {}

    async def async_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.last_update_success:
            return

        protocol, _ = await self.coordinator.data_client.api_node()
        self._state = protocol
        self._attributes = await self.coordinator.data_client.server_status()

    async def async_will_remove_from_hass(self) -> None:
        """Unload when this Entity has been remove from HA."""
        if self._web_socket and self._web_socket.state.is_running:
            await self._web_socket.disconnect()

        await super().async_will_remove_from_hass()

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DOMAIN.upper()} {self.entity_description.key.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        device_info = self._attr_device_info
        if device_info:
            identifiers: set[tuple[str, str]] = device_info.get("identifiers", set())
            domain, suffix = next(iter(identifiers))
        else:
            domain = DOMAIN
            suffix = "user"
        return f"{domain.lower()}_{suffix.lower()}_{self.entity_description.key.lower()}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self._attributes

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:flash" if self._state == "websocket" else "mdi:lock"

    @property
    def _web_socket(self):
        return self.coordinator.web_socket
