"""Common Data for TREM2 component."""

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
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URLS, DOMAIN, EXAMPLE, HA_USER_AGENT, REPORT_URL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class trem2_update_coordinator(DataUpdateCoordinator):
    """Class for handling the TREM data retrieval."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta,
        store_eew: Store,
        store_report: Store,
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
        self._cached_report_data = None
        self._last_update_time = None
        if sys.getsizeof(self._cached_store_data) > 1e6:
            self._cached_store_data = None
        if sys.getsizeof(self._cached_report_data) > 1e6:
            self._cached_report_data = None

        # Coordinator initialization
        self.session = async_get_clientsession(hass)

        # Connection data
        self.http_station, self.http_url = self.get_route()

        # Sensor data
        self.report_data: dict = {}
        self.earthquake_notification: list = []
        self.simulating_notification: list = []
        self.intensity: dict = {}
        # Next Feature: self.rtsData: dict = {}
        # Next Feature: self.tsunamiData: dict = {}

        # Store data
        self.store_eew = store_eew
        self.store_report = store_report

    async def _load_fallback_data(self, resp=None, simulating_notification=None):
        """Fallback to store or example data if response is empty."""
        # Case 1: if response data is not empty
        if resp and len(resp) > 0:
            # Save the last data to the store
            if self._cached_store_data is None or not self._data_equal(self._cached_store_data, resp):
                await self.store_eew.async_save(resp)
                self._cached_store_data = resp

            self.hass.bus.fire(f"{DOMAIN}_notification", {"earthquake": resp}, origin=EventOrigin.remote)

            return resp

        # Case 2: if simulating_notification data is not empty
        if simulating_notification and len(simulating_notification) > 0:
            _LOGGER.debug("Simulating: %s", simulating_notification)

            return simulating_notification

        # Case 3: restore data from the cache
        if self._cached_store_data is not None:
            return self._cached_store_data

        # Case 4: restore data from the store
        store_data = await self.store_eew.async_load()
        self._cached_store_data = store_data or EXAMPLE

        return self._cached_store_data

    async def _load_report_data(self, eq_data: dict):
        """Fallback to report store or update data."""
        report_data: dict = {}

        # Case 1: restore data from the cache
        if self._cached_report_data is not None:
            report_data = self._cached_report_data

        # Case 2: restore data from the store
        if not bool(report_data):
            report_data = await self.store_report.async_load()
            self._cached_report_data = report_data

        # If report data is None, set to empty dict
        if report_data is None:
            report_data = {}

        # Check data is up to date
        report_time = report_data.get("time", 0)
        eew_time = eq_data.get("time")
        if eew_time > report_time:
            try:
                payload = {}
                headers = {
                    ACCEPT: CONTENT_TYPE_JSON,
                    CONTENT_TYPE: CONTENT_TYPE_JSON,
                    USER_AGENT: HA_USER_AGENT,
                }

                response = await self.session.request(
                    method=METH_GET,
                    url=REPORT_URL,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except ClientConnectorError as ex:
                _LOGGER.error(
                    "Failed fetching data from report server(%s), %s",
                    self.http_station,
                    ex.strerror,
                )
            except TimeoutError as ex:
                _LOGGER.error(
                    "Failed fetching data from report server(%s), %s",
                    self.http_station,
                    ex.strerror,
                )
            except Exception:
                _LOGGER.exception(
                    "An unexpected exception occurred fetching the data from report server(%s)",
                    self.http_station,
                )
            else:
                if not response.ok:
                    _LOGGER.error(
                        "Failed fetching data from report server, (HTTP Status Code = %s)",
                        self.http_station,
                        response.status,
                    )
                    return None

                resp = await response.json()
                report_data = resp[0]

                await self.store_report.async_save(resp[0])
                self._cached_report_data = resp[0]

        return self._cached_report_data

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
                _LOGGER.debug("Recv: %s", resp)

                eq_data = await self._load_fallback_data(resp, self.simulating_notification)
                self.earthquake_notification = eq_data

                self.report_data = await self._load_report_data(eq_data[0])
                return self

            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), (HTTP Status Code = %s)",
                self.http_station,
                response.status,
            )

        raise UpdateFailed

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    @staticmethod
    def get_route(exclude: list | None = None):
        """Random the node for fetching data."""
        if exclude is None:
            api_node = BASE_URLS.items()
        else:
            api_node = {k: v for k, v in BASE_URLS.items() if k not in exclude}

        station, base_url = random.choice(list(api_node))
        return (station, f"{base_url}/api/v2/eq/eew?type=cwa")
