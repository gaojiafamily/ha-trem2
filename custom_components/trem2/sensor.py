"""Initialize the SensorEntity for TREM2 component."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any

from homeassistant.components.sensor import (
    EntityCategory,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_LATITUDE,
    ATTR_LOCATION,
    ATTR_LONGITUDE,
    CONF_EMAIL,
)
from homeassistant.core import HomeAssistant, callback
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
    DEFAULT_ICON,
    DOMAIN,
    MANUFACTURER,
    NOTIFICATION_ATTR,
    TZ_TW,
    TZ_UTC,
    UPDATE_COORDINATOR,
    __version__,
)
from .update_coordinator import Trem2UpdateCoordinator

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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TREM sensor from config."""
    domain_data: dict = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: Trem2UpdateCoordinator = domain_data[UPDATE_COORDINATOR]

    # Create the sensor entity
    entities = []
    for entity in SENSOR_ENTITYS:
        if entity.key == "notification":
            entities.append(NotificationSensor(config_entry, coordinator, entity, hass))
        if entity.key == "protocol":
            entities.append(DiagnosticsSensor(config_entry, coordinator, entity, hass))
    async_add_entities(entities, update_before_add=True)


class NotificationSensor(SensorEntity):
    """Defines a earthquake sensor entity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: Trem2UpdateCoordinator,
        description: SensorEntityDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the sensor."""
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

        self._attributes = {}
        self._attr_value = {}
        for k in NOTIFICATION_ATTR:
            self._attr_value[k] = ""
        self._state = ""

    async def async_update(self):
        """Schedule a custom update via the common entity update service."""
        try:
            notification = await self.get_eew_data()
            eew: dict = notification.get("eq", {})
            time: Any | None = eew.get("time")
            time_of_occurrence = ""

            if "serial" in notification:
                notification_id = "-".join(
                    map(
                        str,
                        (
                            notification.get("id", ""),
                            notification.get("serial", ""),
                        ),
                    )
                )
            else:
                pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
                match = re.search(
                    pattern,
                    notification.get("id", ""),
                )
                if match is None:
                    notification_id = ""
                else:
                    notification_id = "-".join(match.groups())

            # formatted the time of occurrence
            if time:
                formatted_time = datetime.fromtimestamp(
                    round(time / 1000),
                    TZ_UTC,
                ).astimezone(TZ_TW)
                time_of_occurrence = formatted_time.strftime("%Y/%m/%d %H:%M:%S")

            # Check state change
            if self._state != notification_id:
                intensitys = {}

                for county, details in notification.get("list", {}).items():
                    county_int = details["int"]
                    intensitys[county] = county_int
                    for town in details["town"]:
                        intensitys[f"{county}{town}"] = county_int

                self._attr_value[ATTR_AUTHOR] = notification.get("author", "")
                self._attr_value[ATTR_ID] = notification_id
                self._attr_value[ATTR_LOCATION] = eew.get("loc", "")
                self._attr_value[ATTR_LONGITUDE] = eew.get("lon", "")
                self._attr_value[ATTR_LATITUDE] = eew.get("lat", "")
                self._attr_value[ATTR_MAG] = eew.get("mag", "")
                self._attr_value[ATTR_DEPTH] = eew.get("depth", "")
                self._attr_value[ATTR_TIME] = time_of_occurrence
                if bool(intensitys):
                    self._attr_value[ATTR_LIST] = intensitys
                else:
                    self._attr_value.pop(ATTR_LIST, None)

                # Update the state
                self._state = notification_id
        except TypeError as ex:
            _LOGGER.error("TypeError occurred while processing earthquake data: %s", ex)
        except AttributeError as ex:
            _LOGGER.error(
                "AttributeError occurred while accessing earthquake data: %s",
                ex,
                exc_info=ex,
            )

        return self

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._update_callback,
            )
        )

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

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

    @callback
    def _update_callback(self) -> None:
        """Handle updated data from the coordinator."""
        if not self._coordinator.last_update_success:
            return

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
            eew_data["list"] = report_data.get("list", None)
            eew_data["md5"] = report_data.get("md5", None)

        # Otherwise, return the notification data
        return eew_data


class DiagnosticsSensor(SensorEntity):
    """Defines a diagnostics sensor entity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: Trem2UpdateCoordinator,
        description: SensorEntityDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._hass = hass

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.options.get(CONF_EMAIL, "user"))},
            "manufacturer": MANUFACTURER,
            "model": "ExpTechTW TREM",
            "sw_version": __version__,
            "name": "Notification",
        }
        self.entity_description = description

        self._state = ""

    async def async_update(self):
        """Schedule a custom update via the common entity update service."""
        self._state = self._coordinator.connection_status()

        return self

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._update_callback,
            )
        )

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

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
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self._coordinator.server_status()

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:flash" if self._state == "websocket" else "mdi:lock"

    @callback
    def _update_callback(self) -> None:
        """Handle updated data from the coordinator."""
        if not self._coordinator.last_update_success:
            return

        self.async_write_ha_state()
