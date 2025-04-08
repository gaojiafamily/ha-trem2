"""Common Data class used by both sensor and entity."""

from __future__ import annotations

from asyncio.exceptions import TimeoutError
from datetime import timedelta
import json
import logging
import random
import sys

from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT

from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URLS, DOMAIN, EXAMPLE, HA_USER_AGENT, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class trem2_update_coordinator(DataUpdateCoordinator):
    """Class for handling the TREM data retrieval."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta,
        store: Store,
    ) -> None:
        """Initialize the data object."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

        # Store data
        self._cached_store_data = None
        self._last_update_time = None

        if sys.getsizeof(self._cached_store_data) > 1e6:
            self._cached_store_data = None

        # Coordinator initialization
        self.session = async_get_clientsession(hass)

        # Connection data
        self.http_station, self.http_url = self.get_route()

        # Sensor data
        self.earthquake_notification: list = []
        # Next Feature: self.intensity: dict = {}
        # Next Feature: self.rtsData: dict = {}
        # Next Feature: self.tsunamiData: dict = {}

        # Store data
        self.store = store

    async def _load_fallback_data(self, resp=None):
        """Fallback to store or example data if response is empty."""
        # Load the last data from the store
        store_data = await self.store.async_load()

        # Case 1: if response data is not empty
        if resp and len(resp) > 0:
            # Save the last data to the store
            if self._cached_store_data is None or not self._data_equal(
                self._cached_store_data, resp
            ):
                await self.store.async_save(resp)
                self._cached_store_data = resp
            return resp

        # Case 2: if response data is empty
        if self._cached_store_data is not None:
            return self._cached_store_data

        # Case 3: if store data is empty
        store_data = await self.store.async_load()
        self._cached_store_data = store_data or EXAMPLE

        return self._cached_store_data

    async def _async_update_data(self):
        """Poll earthquake data."""
        try:
            payload = {}
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await self.session.request(
                method=METH_GET,
                url=self.http_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except ClientConnectorError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.http_station,
                ex.strerror,
            )
        except TimeoutError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.http_station,
                ex.strerror,
            )
        except Exception:
            _LOGGER.exception(
                "An unexpected exception occurred fetching the data from HTTP API(%s)",
                self.http_station,
            )
        else:
            if response.ok:
                resp = await response.json()
                self.earthquake_notification = await self._load_fallback_data(resp)

                # Display received content
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.info("Recv: %s", resp)

                return self

            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), (HTTP Status Code = %s)",
                self.http_station,
                response.status,
            )

        raise UpdateFailed

    def _data_equal(self, a, b):
        """Comparison of data structures."""
        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    def get_route(self, exclude: list | None = None):
        """Random the node for fetching data."""
        if exclude is None:
            api_node = BASE_URLS.items()
        else:
            api_node = {k: v for k, v in BASE_URLS.items() if k not in exclude}

        station, base_url = random.choice(list(api_node))
        return (station, f"{base_url}/api/v2/eq/eew?type=cwa")
