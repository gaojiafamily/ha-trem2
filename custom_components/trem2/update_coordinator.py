"""Common Data for TREM2 component."""

from __future__ import annotations

import asyncio

# from asyncio.exceptions import TimeoutError
from datetime import datetime, timedelta
import json
import logging
import random
import sys

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT

# import async_timeout
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import EventOrigin, HomeAssistant

# from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_VERSION,
    BASE_URLS,
    DOMAIN,
    HA_USER_AGENT,
    REPORT_URL,
    REQUEST_TIMEOUT,
    WS_URLS,
)

_LOGGER = logging.getLogger(__name__)


class ECSManager:
    """Enhanced Computing Service."""

    def __init__(self) -> None:
        """Initialize the Enhanced Computing Service."""
        self.base_url = ""  # Add-on Url

    async def initialize(self) -> bool:
        """Check ECS is available and register service."""
        # If ECS is available

        return False


class ExpTechWSManager:
    """WebSocket connections and message reception."""

    def __init__(self) -> None:
        """Initialize the WebSocket polling."""
        self._retry = 0
        self.exclude_station = []
        self.station = None
        self.base_url = None

    # async def reconnect(self, session: ClientSession):
    # await self.disconnect()
    # await self.connect(session)

    # async def connect(self, session: ClientSession)
    # asyncio.create_task(self.listen())

    # async def disconnect(self, session: ClientSession):
    # await session.close()

    # def listen(self):

    # def handle(self):
    # """register service or parse package."""

    # async def resp(self):
    # return []

    async def initialize_route(self, **kwargs) -> str | bool:
        """Random the node for fetching data."""
        base_url = kwargs.get("base_url", None)
        if base_url:
            self.exclude_station = []
            self.station = base_url
            self.base_url = base_url

            trem2_update_coordinator.async_request_refresh()
            return base_url

        station = kwargs.get("station", None)
        if station in WS_URLS:
            self.exclude_station = []
            self.station = station
            self.base_url = WS_URLS[station]

            trem2_update_coordinator.async_refresh()
            return station

        exclude = kwargs.get("exclude", [])
        api_node = [k for k in WS_URLS.keys() if k not in exclude]
        if len(api_node) > 0:
            self.station = random.choice(api_node)
            self.base_url = WS_URLS[self.station]
        else:
            _LOGGER.error(
                "Unable to connect to the %s node. No available nodes, the service will be suspended",
                ",".join(self.exclude_station),
                self.station,
            )
            return False

        if len(exclude) > 0:
            _LOGGER.warning(
                "Unable to connect to the %s node. attempting to switch to the %s node",
                ",".join(self.exclude_station),
                self.station,
            )

        return self.station


class ExpTechHTTPManager:
    """Https connections and message reception."""

    def __init__(self) -> None:
        """Initialize the Https polling."""
        self.exclude_station = []
        self.station = None
        self.base_url = None
        self.websocket = False

    async def fetch_eew(self, session: ClientSession) -> list | None:
        """Fetch earthquake data from the ExpTech server."""
        try:
            payload = {}
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
                method=METH_GET,
                url=self.base_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except ClientConnectorError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.station,
                ex.strerror,
            )
        except TimeoutError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.station,
                ex.strerror,
            )
        except Exception:
            _LOGGER.exception(
                "An unexpected exception occurred fetching the data from HTTP API(%s)",
                self.station,
            )
        else:
            if response.ok:
                if len(self.exclude_station) > 0:
                    self.exclude_station = []

                return await response.json()

            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), (HTTP Status Code = %s)",
                self.station,
                response.status,
            )

        return None

    async def fetch_report(self, session: ClientSession, local_report: dict) -> list | None:
        """Fetch report summary data from the ExpTech server."""
        try:
            payload = {}
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
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
                    local_report_id = local_report.get("id", "")

                    # Check if the report data is up to date
                    if fetch_report_id not in {"", local_report_id}:
                        return await self.fetch_report_detail(
                            session,
                            fetch_report_id,
                        )
                else:
                    _LOGGER.debug("Report data is empty")
            else:
                _LOGGER.error(
                    "Failed fetching data from report server, (HTTP Status Code = %s)",
                    response.status,
                )

            return None

    async def fetch_report_detail(self, session: ClientSession, report_id) -> list | None:
        """Fetch report detail data from the report server."""
        try:
            payload = {}
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
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

        _LOGGER.error(
            "Failed fetching data from report server, (HTTP Status Code = %s)",
            response.status,
        )

        return None

    async def initialize_route(self, **kwargs) -> str | bool:
        """Random the node for fetching data."""
        base_url = kwargs.get("base_url", None)
        if base_url:
            self.exclude_station = []
            self.station = base_url
            self.base_url = base_url

            return base_url

        station = kwargs.get("station", None)
        if station in BASE_URLS:
            self.exclude_station = []
            self.station = station
            self.base_url = "{base_url}/api/v{api_version!s}/eq/eew".format(
                api_version=API_VERSION,
                base_url=BASE_URLS[station],
            )

            return station

        exclude = kwargs.get("exclude", [])
        api_node = [k for k in BASE_URLS.keys() if k not in exclude]
        if len(api_node) > 0:
            self.station = random.choice(api_node)
            self.base_url = "{base_url}/api/v{api_version!s}/eq/eew".format(
                api_version=API_VERSION,
                base_url=BASE_URLS[self.station],
            )
        else:
            _LOGGER.error(
                "Unable to connect to the %s node. No available nodes, the service will be suspended",
                ",".join(self.exclude_station),
            )
            return False

        if len(exclude) > 0:
            _LOGGER.warning(
                "Unable to connect to the %s node. attempting to switch to the %s node",
                ",".join(self.exclude_station),
                self.station,
            )

        return self.station


class trem2_update_coordinator(DataUpdateCoordinator):
    """Class for handling the TREM data retrieval."""

    def __init__(
        self,
        hass: HomeAssistant,
        store_eew: Store,
        store_report: Store,
    ) -> None:
        """Initialize the Data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )

        # Cache data
        self._cached_eew_data = None
        self._cached_report_data = None
        if sys.getsizeof(self._cached_eew_data) > 1e6:
            self._cached_eew_data = None
        if sys.getsizeof(self._cached_report_data) > 1e6:
            self._cached_report_data = None

        # Store data
        self.store_eew = store_eew
        self.store_report = store_report
        self.report_fetch_time = 0

        # Coordinator initialization
        self.session = async_get_clientsession(hass)
        self.http_manager = ExpTechHTTPManager()
        self.ws_manager = ExpTechWSManager()
        self._initialize_task = asyncio.create_task(self._initialize())
        self.retry_backoff = 1
        self.base_interval = timedelta(seconds=5)
        self.max_interval = timedelta(minutes=15)

        # Sensor data
        self.report_data: list = []
        self.earthquake_notification: list = []
        self.simulating_notification: list = []
        self.intensity: dict = {}
        # Next Feature: self.rtsData: dict = {}
        # Next Feature: self.tsunamiData: dict = {}

    async def _initialize(self) -> bool:
        """Initialize for fetching data."""
        self.update_interval = self.base_interval

        http_exclude = self.http_manager.exclude_station
        if self.http_manager.station is not None:
            http_exclude.append(self.http_manager.station)
        station = await self.http_manager.initialize_route(exclude=http_exclude)  # Required

        # ECS OR Webscoket
        # await ECSManager.initialize()
        # await ExpTechWSManager.initialize_route()

        # Event fired
        event_data = {
            "type": "server_status",
            "current_node": station if station else None,
            "unavailable": self.http_manager.exclude_station,
            "protocol": "ws" if self.http_manager.websocket else "http",
        }
        self.hass.bus.fire(
            f"{DOMAIN}_status",
            event_data,
        )

        # Max retries, raise exception
        if not station:
            self.http_manager.station = None
            self.ws_manager.station = None
            raise ConnectionRefusedError("ExpTech server connection failures")

    async def _async_update_data(self):
        """Poll earthquake data."""
        if self._initialize_task:
            if not self._initialize_task.done():
                return

            if self._initialize_task.exception() is not None:
                self.http_manager.exclude_station = []
                _LOGGER.error(self._initialize_task.exception())

        resp = await self.http_manager.fetch_eew(self.session)
        if resp is None:
            self._initialize_task = asyncio.create_task(self._initialize())
            self.retry_backoff = min(self.retry_backoff * 2, 256)
            new_interval = min(self.base_interval * self.retry_backoff, self.max_interval)
            self.update_interval = new_interval
            _LOGGER.error(
                "Update failed, the next attempt will be in %s seconds",
                new_interval.total_seconds(),
            )
            raise UpdateFailed()

        self.http_manager.exclude_station = []
        self.retry_backoff = 1

        _LOGGER.debug("Recv: %s", resp)
        self.earthquake_notification = await self._load_fallback_data(
            resp,
            self.simulating_notification,
        )
        self.report_data = await self._load_report_data(
            self.earthquake_notification,
            self.simulating_notification,
        )

    async def _load_fallback_data(self, resp=None, simulator=None):
        """Fallback to store or update data."""
        # Case 1: if simulator data is not empty
        if simulator and len(simulator) > 0:
            _LOGGER.debug("Simulating: %s", simulator)
            return simulator

        # Case 2: if response data is not empty
        if resp and len(resp) > 0:
            # Save the last data to the store
            if not self._data_equal(self._cached_eew_data, resp):
                await self.store_eew.async_save(resp)
                self._cached_eew_data = resp

            self.hass.bus.fire(
                f"{DOMAIN}_notification",
                {"earthquake": resp},
                origin=EventOrigin.remote,
            )

        # Case 3: if cached is empty, restore data from the store
        if self._cached_eew_data is None:
            store_data = await self.store_eew.async_load()
            self._cached_eew_data = store_data or [{}]

        return self._cached_eew_data

    async def _load_report_data(self, eq_data, simulator):
        """Fallback to report store or update data."""
        # Extract data
        eq: dict = eq_data[0] if isinstance(eq_data, list) and len(eq_data) > 0 else eq_data
        report_data = self._cached_report_data or [{}]

        # if simulating earthquake, return empty report data
        if simulator and len(simulator) > 0:
            return [{}]

        # if report is empty, restore data from the store
        local_report: dict = report_data[0] if isinstance(report_data, list) and len(report_data) > 0 else report_data
        if not bool(local_report):
            report_data = await self.store_report.async_load()
            self._cached_report_data = report_data

        # Check data is up to date
        report_time = local_report.get("time", 0)
        eew_time = eq.get("time", 1)
        if eew_time > report_time:
            # Check if the report data is older than 5 minutes
            if abs(self.report_fetch_time - datetime.now().timestamp()) < 300:
                return self._cached_report_data

            # Execute fetching data from the report server
            self._cached_report_data = await self.http_manager.fetch_report(self.session, local_report)
            await self.store_report.async_save(self._cached_report_data)
            self.report_fetch_time = datetime.now().timestamp()

            self.hass.bus.fire(
                f"{DOMAIN}_report",
                self._cached_report_data,
                origin=EventOrigin.remote,
            )

        return self._cached_report_data

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
