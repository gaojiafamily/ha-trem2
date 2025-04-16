"""Common Data for TREM2 component."""

from __future__ import annotations

from asyncio.exceptions import TimeoutError
from datetime import datetime, timedelta
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

from .const import BASE_URLS, DOMAIN, HA_USER_AGENT, REPORT_URL, REQUEST_TIMEOUT

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
        self.report_fetch_time = 0

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

    async def _load_fallback_data(self, resp=None, simulator=None):
        """Fallback to store or example data if response is empty."""
        # Case 1: if response data is not empty
        if resp and len(resp) > 0:
            # Save the last data to the store
            if self._cached_store_data is None or not self._data_equal(self._cached_store_data, resp):
                await self.store_eew.async_save(resp)
                self._cached_store_data = resp

            self.hass.bus.fire(f"{DOMAIN}_notification", {"earthquake": resp}, origin=EventOrigin.remote)
            return resp

        # Case 2: if simulator data is not empty
        if simulator and len(simulator) > 0:
            _LOGGER.debug("Simulating: %s", simulator)
            return simulator

        # Case 3: if cached is empty, restore data from the store
        if self._cached_store_data is None:
            store_data = await self.store_eew.async_load()
            self._cached_store_data = store_data or [{}]

        # Case 4: Default return cache data
        return self._cached_store_data

    async def _load_report_data(self, eq_data, simulator):
        """Fallback to report store or update data."""
        # Extract data
        eq: dict = eq_data[0] if isinstance(eq_data, list) and len(eq_data) > 0 else eq_data
        report_data = self._cached_report_data or [{}]

        # if simulating earthquake, return empty report data
        if simulator and len(simulator) > 0:
            return [{}]

        # if report is empty, restore data from the store
        report: dict = report_data[0] if isinstance(report_data, list) and len(report_data) > 0 else report_data
        if not bool(report):
            report_data = await self.store_report.async_load()
            self._cached_report_data = report_data

        # Check data is up to date
        report_time = report.get("time", 0)
        eew_time = eq.get("time", 1)
        if eew_time > report_time:
            # Execute fetching data from the report server
            delay5min = abs(self.report_fetch_time - datetime.now().timestamp()) < 300

            # Check if the report data is older than 5 minutes
            if delay5min:
                return self._cached_report_data

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
                _LOGGER.error("Failed fetching data from report server, %s", ex.strerror)
            except TimeoutError as ex:
                _LOGGER.error("Failed fetching data from report server, %s", ex.strerror)
            except Exception:
                _LOGGER.exception("An unexpected exception occurred fetching the data from report server")
            else:
                if response.ok:
                    resp = await response.json()

                    # Check if the report data is empty
                    if len(resp) > 0:
                        # Extract data
                        fetch_report: dict = resp[0]
                        fetch_report_id = fetch_report.get("id", "")
                        local_report_id = report.get("id", "")

                        # Check if the report data is up to date
                        if fetch_report_id not in {"", local_report_id}:
                            self._cached_report_data = await self._fetch_report_detail(fetch_report_id)
                            await self.store_report.async_save(self._cached_report_data)

                            self.hass.bus.fire(
                                f"{DOMAIN}_report",
                                self._cached_report_data,
                                origin=EventOrigin.remote,
                            )
                    else:
                        _LOGGER.debug("Report data is empty")
                else:
                    _LOGGER.error(
                        "Failed fetching data from report server, (HTTP Status Code = %s)",
                        response.status,
                    )

        return self._cached_report_data

    async def _fetch_report_detail(self, report_id):
        """Fetch report detail data from the report server."""
        try:
            payload = {}
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await self.session.request(
                method=METH_GET,
                url=f"{REPORT_URL}/{report_id}",
                data=json.dumps(payload),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except ClientConnectorError as ex:
            _LOGGER.error("Failed fetching data from report server, %s", ex.strerror)
        except TimeoutError as ex:
            _LOGGER.error("Failed fetching data from report server, %s", ex.strerror)
        except Exception:
            _LOGGER.exception("An unexpected exception occurred fetching the data from report server")
        else:
            if response.ok:
                return await response.json()

        _LOGGER.error("Failed fetching data from report server, (HTTP Status Code = %s)", response.status)
        return None

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

                simulator = self.simulating_notification
                eq_data = await self._load_fallback_data(
                    resp,
                    simulator,
                )
                self.earthquake_notification = eq_data

                self.report_data = await self._load_report_data(eq_data, simulator)
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
