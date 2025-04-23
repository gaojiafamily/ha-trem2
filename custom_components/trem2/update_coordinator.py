"""Common Data for TREM2 component."""

from __future__ import annotations

import asyncio

from asyncio import Task
from asyncio.exceptions import TimeoutError
from datetime import datetime, timedelta
import json
import logging
import random
import sys

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT

from homeassistant.const import CONF_API_TOKEN, CONTENT_TYPE_JSON, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from urllib.parse import ParseResult, urlparse, parse_qs, urlencode, urlunparse

from .const import (
    API_VERSION,
    BASE_URLS,
    CONF_PROVIDER,
    DOMAIN,
    HA_USER_AGENT,
    PROVIDER_OPTIONS,
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
        """Check if ECS is available and register the service.

        Returns:
            True if ECS is available and registered, otherwise False.
        """
        # TODO: Implement ECS availability check and registration logic.

        return False


class ExpTechWSManager:
    """Manage WebSocket connections and message reception."""

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self.exclude_station = []
        self.base_url = None
        self.station = None
        self._conn: ClientWebSocketResponse = None
        self.session: ClientSession = None
        self.access_token = "c0d30WNER$JTGAO"
        self.credentials = None
        self.subscrib_service = None
        self._register_service = [
            "websocket.eew",
            "websocket.tsunami",
            "websocket.report",
            "trem.rts",
            # "trem.rtw",
            "cwa.intensity",
            "trem.intensity",
        ]
        self.lock = asyncio.Lock()
        self._task_list = []
        self._keepalive_task: Task = None
        self.receive_task: Task = None
        self.hass: HomeAssistant = None
        self.is_running = False
        self._message = ""

    async def reconnect(self):
        """Reconnect the WebSocket connection.

        Closes the existing connection if present, then establishes a new connection.
        """
        async with self.lock:
            await self.disconnect()
            await self.connect()

    async def disconnect(self):
        """Close the active WebSocket connection and reset credentials."""
        if self._conn:
            await self._conn.close()
            self._conn = None

        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None

        self.credentials = None
        self.is_running = False

    async def connect(self, params=None):
        """Establish a new WebSocket connection.

        Args:
            params (dict, optional): Query parameters to append to the URL.

        Returns:
            ClientWebSocketResponse: The connected WebSocket object, or None if session is not set.
        """
        if self.is_running:
            return

        if params is None:
            params = {}

        # WSManager is initializing
        if self.session is None:
            return None

        # Re-download ExpTech VIP Certification
        if self.credentials is None:
            self.credentials = {
                "type": "start",
                "key": self.access_token,
                "service": self._register_service,
            }

        # Establishing a connection and verify
        self.base_url = self._add_url_query(self.base_url, params)
        headers = {
            USER_AGENT: HA_USER_AGENT,
        }
        self._conn = await self.session.ws_connect(
            self.base_url,
            headers=headers,
        )
        await self._conn.send_json(self.credentials)

        def log_task_exception(task: Task):
            if task.cancelled():
                _LOGGER.debug("Background task was cancelled (Home Assistant is stopping)")
                return

            try:
                exc = task.exception()
            except asyncio.CancelledError:
                _LOGGER.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
                return
            except Exception as ex:
                _LOGGER.error("Error retrieving task exception: %s", ex, exc_info=True)
                return

            if exc:
                _LOGGER.error("ExpTech listen task failed: %s", exc, exc_info=exc)

        self._keepalive_task = self.hass.async_create_background_task(
            self._keepalive(),
            name="exptech_ws_heartbeat",
        )
        self._keepalive_task.add_done_callback(log_task_exception)
        self.receive_task = self.hass.async_create_background_task(
            self.listen(),
            name="exptech_ws_listener",
        )
        self.receive_task.add_done_callback(log_task_exception)

        return self._conn

    async def listen(self):
        """Listen for incoming WebSocket messages and process events.

        Continuously receives messages from the active WebSocket connection.
        If the connection is lost, attempts to reconnect.
        """
        self.is_running = True
        retries = 0
        max_retries = 5

        while self.is_running:
            await asyncio.sleep(1)
            if self._conn is None or self._conn.closed:
                continue

            # Extract the message type and data from the WSMessage object.
            try:
                retries = 0

                raw_message = await self._conn.receive()
                raw_type = raw_message.type
                raw_data = raw_message.data

                # Process the message type and data using the custom handler.
                self._message = await self._handle(raw_type, raw_data)
            except (RuntimeError, ConnectionResetError):
                retries += 1
                if retries >= max_retries:
                    _LOGGER.error("Max retries, WebSocket connection failures")
                    break
                await asyncio.sleep(2**retries)
                await self.reconnect()

    async def _handle(self, type, data):
        """Handle incoming WebSocket messages based on type and event."""
        if type in (WSMsgType.close, WSMsgType.closed, WSMsgType.closing):
            return None

        payload: dict = json.loads(data)
        event = payload.get("type")
        msg_data: dict = payload.get("data", {})

        if event == "verify":
            await self._conn.send_json(self.credentials)
            return msg_data

        if event == "info":
            msg_code = msg_data.get("code")

            if msg_code == 200:
                self.subscrib_service = msg_data.get("list", [])
                return msg_data

            if msg_code == 401:
                self.credentials = None

            if msg_code == 503:
                await asyncio.sleep(5)

        if event in ("data", "ntp"):
            return msg_data

        _LOGGER.debug(event)
        return None

    async def _keepalive(self):
        """Perform WebSocket pingpong."""
        while self.is_running:
            await asyncio.sleep(30)
            if self._conn and not self._conn.closed:
                await self._conn.ping()

    async def recv(self):
        """Fetch data from the ExpTech server via WebSocket.

        Returns:
            list | None: The received message(s) or None if not available.
        """
        if not self._conn:
            raise ConnectionResetError

        if self._message is None:
            raise RuntimeError

        return self._message

    async def initialize_route(self, **kwargs) -> str | bool:
        """Randomly select a node for WebSocket connection.

        Args:
            base_url (str, optional): Specific base URL to use.
            station (str, optional): Specific station to use.
            exclude (list, optional): List of nodes to exclude.

        Returns:
            str | bool: The selected station or False if no nodes are available.
        """
        base_url = kwargs.get("base_url", "")
        if bool(base_url):
            self.exclude_station = []
            self.base_url = base_url
            self.station = base_url

            return base_url

        station = kwargs.get("station", "")
        if station in WS_URLS:
            self.exclude_station = []
            self.station = station
            self.base_url = WS_URLS[station]

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
            )
            return False

        if len(exclude) > 0:
            _LOGGER.warning(
                "Unable to connect to the %s node. attempting to switch to the %s node",
                ",".join(self.exclude_station),
                self.station,
            )

        return self.station

    def log_task_exception(task: Task):
        """Log exceptions or cancellations from a background task.

        This function should be used as a done callback for asyncio tasks.
        It logs any unhandled exceptions or cancellations that occur during
        the execution of the background task.
        """
        if task.cancelled():
            _LOGGER.debug("Background task was cancelled (Home Assistant is stopping)")
            return

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            _LOGGER.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
            return
        except Exception as ex:
            _LOGGER.error("Error retrieving task exception: %s", ex, exc_info=True)
            return

        if exc:
            _LOGGER.error("ExpTech WS lister task failed: %s", exc, exc_info=exc)

    def _add_url_query(self, base_url, params):
        """Parse and add or update query parameters to the URL.

        Args:
            base_url (str): The base URL.
            params (dict): The query parameters to add or update.

        Returns:
            str: The new URL with updated query parameters.
        """
        parsed: ParseResult = urlparse(base_url)

        query = parse_qs(parsed.query)
        query.update(params)

        new_query = urlencode(query, doseq=True)
        new_url = urlunparse(parsed._replace(query=new_query))

        return new_url


class ExpTechHTTPManager:
    """Manage HTTP connections and message reception."""

    def __init__(self) -> None:
        """Initialize the HTTP manager."""
        self.exclude_station = []
        self.station = None
        self.base_url = None
        self.websocket: ClientWebSocketResponse = None

    async def fetch_eew(self, session: ClientSession, params=None) -> list | None:
        """Fetch earthquake data from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.
        """
        if params is None:
            params = {}

        # Fetch eew data
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
                method=METH_GET,
                url=self.base_url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.station,
                ex.strerror,
            )
        except RuntimeError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.station,
                str(ex),
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
        """Fetch report summary from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.
        """
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
                method=METH_GET,
                url=REPORT_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
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
        """Fetch report detail from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.
        """
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await session.request(
                method=METH_GET,
                url=f"{REPORT_URL}/{report_id}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
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
        """Randomly select a node for HTTP connection.

        Args:
            base_url (str, optional): Specific base URL to use.
            station (str, optional): Specific station to use.
            exclude (list, optional): List of nodes to exclude.

        Returns:
            str | bool: The selected station or False if no nodes are available.
        """
        base_url = kwargs.get("base_url", "")
        if bool(base_url):
            self.exclude_station = []
            self.base_url = base_url
            self.station = base_url

            return base_url

        station = kwargs.get("station", "")
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

        # Coordinator initialization
        self.session = async_get_clientsession(hass)
        self.ecs_manager = ECSManager()
        self.http_manager = ExpTechHTTPManager()
        self.ws_manager = ExpTechWSManager()
        self.use_http_fallback = False
        self._initialize_task = None
        self.retry_backoff = 1
        self.station = None
        self.base_interval = timedelta(seconds=5)
        self.max_interval = timedelta(minutes=15)
        self._unsub_shutdown = None
        self.params = {}

        # Store data
        self.store_eew = store_eew
        self.store_report = store_report
        self.report_fetch_time = 0

        # Sensor data
        self.report_data = {}
        self.earthquake_notification = {}
        self.simulating_notification = {}
        self.intensity = {}
        self.rtsData = {}
        self.tsunamiData = {}

    async def _initialize(self) -> bool:
        """Initialize for fetching data."""
        self.update_interval = self.base_interval

        # Disconnect websocket if running
        if self.ws_manager.is_running:
            await self.ws_manager.disconnect()

        # Setup config entry options to params
        config_options = self.config_entry.options
        _provider = config_options.get(CONF_PROVIDER, None)
        provider_options = {k: v for k, v in PROVIDER_OPTIONS}
        publisher = provider_options.get(_provider, None)
        if len(publisher) > 0:
            self.params["type"] = publisher

        # Setup Http fetch method
        http_exclude = self.http_manager.exclude_station
        if bool(self.http_manager.station):
            http_exclude.append(self.http_manager.station)
        self.station = await self.http_manager.initialize_route(exclude=http_exclude)

        # Setup WebSocket fetch method
        _api_token = config_options.get(CONF_API_TOKEN, "")
        if bool(_api_token):
            ws_exclude = self.ws_manager.exclude_station
            if bool(self.ws_manager.station):
                ws_exclude.append(self.ws_manager.station)
            self.station = await self.ws_manager.initialize_route()

            async with self.ws_manager.lock:
                self.ws_manager.access_token = _api_token
                self.ws_manager.session = self.session
                self.ws_manager.hass = self.hass
                self.http_manager.websocket = await self.ws_manager.connect(self.params)

                ws_receive_task = self.ws_manager.receive_task
                if not ws_receive_task or ws_receive_task.done():
                    ws_receive_task = self.hass.async_create_background_task(
                        self.ws_manager.listen(),
                        name="exptech_websocket_listener",
                    )
                    ws_receive_task.add_done_callback(self._log_task_exception)

            self.update_interval = timedelta(seconds=1)

        # Setup ECS Service if online
        # await self.ecs_manager.initialize()

        # If max retries, raise connection failures
        if self.station:
            self._server_status_event(unavailable=ws_exclude)
        else:
            self.http_manager.station = None
            self.ws_manager.station = None
            raise ConnectionRefusedError("ExpTech server connection failures")

    async def async_register_shutdown(self):
        """Register shutdown on HomeAssistant stop."""

        async def _on_hass_stop(event):
            await self.async_shutdown()

        self._unsub_shutdown = self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_hass_stop)

    async def async_shutdown(self):
        """Perform websocket disconnect."""
        if not self.http_manager.websocket.closed:
            await self.ws_manager.disconnect()

    async def _async_update_data(self):
        """Poll earthquake data."""
        resp = None
        self.use_http_fallback = False

        # 協調員初始化
        if self._initialize_task:
            if not self._initialize_task.done():
                return

            if bool(self._initialize_task.exception()):
                self.http_manager.exclude_station = []
                _LOGGER.error(self._initialize_task.exception())
        else:
            self._initialize_task = self.hass.async_create_task(self._initialize(), name="trem2_initializing")
            self._initialize_task.add_done_callback(self._log_task_exception)
            return

        # 優先使用 WebSocket 獲取資料
        if self.ws_manager.is_running:
            try:
                if self.ws_manager.credentials is None:
                    await self.ws_manager.disconnect()
                    raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

                if self.ws_manager.subscrib_service in (None, []):
                    await self.ws_manager.disconnect()
                    raise ConfigEntryAuthFailed("The ExpTech VIP has expired, Please re-subscribe.")

                resp = await self.ws_manager.recv()
            except (ConnectionResetError, RuntimeError) as ex:
                self.use_http_fallback = True
                self._server_status_event()
                _LOGGER.warning("WebSocket connection error: %s, falling back to HTTP", ex)

        if not self.ws_manager.is_running or self.use_http_fallback:
            resp = await self.http_manager.fetch_eew(self.session, self.params)

        # 只在純 HTTP 模式或降級時應用指數退避
        if not self.ws_manager.is_running or resp is None or self.use_http_fallback:
            self._initialize_task = None
            self.retry_backoff = min(self.retry_backoff * 2, 256)
            new_interval = min(self.base_interval * self.retry_backoff, self.max_interval)
            self.update_interval = new_interval
            _LOGGER.error("Update failed, next attempt in %.1f seconds", new_interval.total_seconds())
        else:
            self.retry_backoff = 1
            self.http_manager.exclude_station = []
            self.ws_manager.exclude_station = []

        # Parse eew and report data
        _LOGGER.debug("Recv: %s", resp)
        self.earthquake_notification = await self._load_eew_data(
            resp,
            self.simulating_notification,
        )
        self.report_data = await self._load_report_data(
            resp,
            self.simulating_notification,
        )

    async def _load_eew_data(self, resp=None, simulator=None):
        """Fallback to store or update data."""
        try:
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
        except AttributeError as ex:
            _LOGGER.error("AttributeError occurred while accessing eew data: %s", str(ex), exc_info=ex)

        return self._cached_eew_data

    async def _load_report_data(self, eq_data, simulator):
        """Fallback to report store or update data."""
        try:
            # Extract data
            eq: dict = eq_data[0] if isinstance(eq_data, list) and len(eq_data) > 0 else eq_data
            report_data = self._cached_report_data or [{}]

            # if simulating earthquake, return empty report data
            if simulator and len(simulator) > 0:
                return [{}]

            # if report is empty, restore data from the store
            local_report: dict = (
                report_data[0] if isinstance(report_data, list) and len(report_data) > 0 else report_data
            )
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
        except AttributeError as ex:
            _LOGGER.error("AttributeError occurred while accessing report data: %s", str(ex), exc_info=ex)

        return self._cached_report_data

    def _server_status_event(self, **kwargs):
        """Server status update trigger event."""
        api_node = kwargs.get("station", self.station)
        unavailable = kwargs.get("unavailable", [])
        protocol = self._connection_status()

        event_data = {
            "type": "server_status",
            "current_node": api_node,
            "unavailable": unavailable,
            "protocol": protocol,
        }
        self.hass.bus.fire(
            f"{DOMAIN}_status",
            event_data,
        )

    def _connection_status(self) -> str:
        """Return current connection mode."""
        if self.ws_manager.is_running:
            return "websocket"

        return "http"

    def _log_task_exception(self, task: Task):
        """Log exceptions or cancellations from a background task.

        This function should be used as a done callback for asyncio tasks.
        It logs any unhandled exceptions or cancellations that occur during
        the execution of the background task.
        """
        if task.cancelled():
            _LOGGER.debug("Background task was cancelled (Home Assistant is stopping)")
            return

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            _LOGGER.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
            return
        except Exception as ex:
            _LOGGER.error("Error retrieving task exception: %s", ex, exc_info=True)
            return

        if exc:
            _LOGGER.error("Initialize task failed: %s", exc, exc_info=exc)

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
