"""Common Data for TREM2 component."""

from __future__ import annotations

import asyncio
from asyncio import Task
import dataclasses
from datetime import datetime, timedelta
import json
import logging
import random
import sys

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT
from websocket import WebSocketApp as wsc, enableTrace

from homeassistant.const import CONF_API_TOKEN, CONTENT_TYPE_JSON, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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


class ExpTechHTTPManager:
    """Manage HTTP connections and message reception."""

    def __init__(self) -> None:
        """Initialize the HTTP manager."""
        self.exclude_station = []
        self.station = None
        self.base_url = None
        self.session: ClientSession = None
        self.websocket: wsc = None

    async def fetch_eew(self, params=None) -> list | None:
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

            response = await self.session.request(
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
                str(ex),
            )
        except RuntimeError as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.station,
                str(ex),
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

        raise RuntimeError("An error occurred during message reception")

    async def fetch_report(self, local_report: dict) -> list | None:
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

            response = await self.session.request(
                method=METH_GET,
                url=REPORT_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            _LOGGER.error("Failed fetching data from report server, %s", str(ex))
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
                        return await self.fetch_report_detail(fetch_report_id)
                else:
                    _LOGGER.debug("Report data is empty")
            else:
                _LOGGER.error(
                    "Failed fetching data from report server, (HTTP Status Code = %s)",
                    response.status,
                )

            return None

    async def fetch_report_detail(self, report_id) -> list | None:
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

            response = await self.session.request(
                method=METH_GET,
                url=f"{REPORT_URL}/{report_id}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            _LOGGER.error("Failed fetching data from report server, %s", str(ex))
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
            **kwargs: Arbitrary keyword arguments. Can include:
                - base_url (str, optional): Specific base URL to use.
                - station (str, optional): Specific station to use.
                - exclude (list, optional): List of nodes to exclude.

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
            self.base_url = f"{BASE_URLS[station]}/api/v{API_VERSION}/eq/eew"

            return station

        exclude = kwargs.get("exclude", [])
        api_node = [k for k in BASE_URLS if k not in exclude]
        if len(api_node) > 0:
            self.station = random.choice(api_node)
            self.base_url = f"{BASE_URLS[self.station]}/api/v{API_VERSION}/eq/eew"
        else:
            _LOGGER.error(
                "No available nodes (%s), the service will be suspended",
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


@dataclasses.dataclass
class WSConnectionConf:
    """Manage ExpTech WebSocket configuration."""

    access_token = "c0d30WNER$JTGAO"
    base_url: str | None = None
    params: dict | None = None
    register_service = [
        "websocket.eew",
        "websocket.tsunami",
        "websocket.report",
        "trem.rts",
        # "trem.rtw",
        "cwa.intensity",
        "trem.intensity",
    ]


@dataclasses.dataclass
class WSConnectionState:
    """Manage ExpTech WebSocket Connection State."""

    conn: wsc | None = None
    credentials: dict | None = None
    exclude_station = []
    station = None
    is_running: bool = False
    message: str = ""
    exception: Exception | None = None
    subscrib_service: list | None = None


class ExpTechWSManager:
    """Manage WebSocket connections and message reception."""

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self.ws_config = WSConnectionConf()
        self.ws_state = WSConnectionState()
        self.hass: HomeAssistant = None

    def disconnect(self):
        """Close the active WebSocket connection and reset credentials."""
        if self.ws_state.conn:
            self.ws_state.conn.close()
            self.ws_state.conn = None

    def connect(self):
        """Establish a new WebSocket connection."""
        if self.ws_state.conn:
            self.ws_state.conn.close()

        # Establishing a connection and register event
        enableTrace(
            _LOGGER.isEnabledFor(logging.DEBUG),
            level="DEBUG",
        )
        headers = {
            USER_AGENT: HA_USER_AGENT,
        }
        self.ws_state.conn = wsc(
            self.ws_config.base_url,
            header=headers,
            on_open=self._verify,
            on_message=self._socket_handle,
            on_error=self._socket_error,
            on_close=self._socket_close,
        )
        self.ws_state.conn.run_forever(reconnect=5)

        return self.ws_state.conn

    def _verify(self, ws: wsc):
        """Handle the WebSocket connection opening event."""
        self.ws_state.exception = None
        if self.ws_state.credentials is None:
            self.ws_state.credentials = {
                "type": "start",
                "key": self.ws_config.access_token,
                "service": self.ws_config.register_service,
            }

            if self.ws_config.params:
                self.ws_state.credentials.setdefault("config", self.ws_config.params)

        ws.send(json.dumps(self.ws_state.credentials))

    def _socket_close(self, ws, close_status_code, close_msg):
        """Handle the WebSocket connection disconnect event."""
        if close_status_code == 999 or self.ws_state.exception is SystemExit():
            self.ws_state.conn = None
            self.ws_state.credentials = None
            self.ws_state.is_running = False
        else:
            self.connect()

    def _socket_handle(self, ws: wsc, message):
        """Handle incoming WebSocket messages and process events."""
        payload: dict = json.loads(message)
        event = payload.get("type")
        msg_data: dict = payload.get("data")

        if event != "ntp" and msg_data is None:
            self.ws_state.message = None
            return

        if event == "verify":
            self._verify(ws)
            return

        if event == "info":
            msg_code = msg_data.get("code")

            if msg_code == 200:
                self.ws_state.subscrib_service = msg_data.get("list", [])

            if msg_code == 401:
                self.ws_state.credentials = None
                self.ws_state.message = None
                return

        self.ws_state.is_running = True
        self.ws_state.message = msg_data

    def _socket_error(self, ws, error):
        """Handle the WebSocket connection exception event."""
        self.ws_state.exception = error

        if error is not SystemExit():
            _LOGGER.debug("WebSocket error: %s", repr(error))

    async def recv(self):
        """Fetch data from the ExpTech server via WebSocket.

        Returns:
            list | None: The received message(s) or None if not available.

        """
        if self.ws_state.conn is None:
            raise ConnectionResetError

        return self.ws_state.message

    async def initialize_route(self, **kwargs) -> str | bool:
        """Randomly select a node for WebSocket connection.

        Args:
            **kwargs: Arbitrary keyword arguments. Can include:
                - base_url (str, optional): Specific base URL to use.
                - station (str, optional): Specific station to use.
                - exclude (list, optional): List of nodes to exclude.

        Returns:
            str | bool: The selected station or False if no nodes are available.

        """
        base_url = kwargs.get("base_url", "")
        if bool(base_url):
            self.ws_state.exclude_station = []
            self.ws_config.base_url = base_url
            self.ws_state.station = base_url

            return base_url

        station = kwargs.get("station", "")
        if station in WS_URLS:
            self.ws_state.exclude_station = []
            self.ws_config.base_url = WS_URLS[station]
            self.ws_state.station = station

            return station

        exclude = kwargs.get("exclude", [])
        api_node = [k for k in WS_URLS if k not in exclude]
        if len(api_node) > 0:
            self.ws_state.station = random.choice(api_node)
            self.ws_config.base_url = WS_URLS[self.ws_state.station]
        else:
            _LOGGER.error(
                "No available nodes (%s), the service will be suspended",
                ",".join(self.ws_state.exclude_station),
            )
            return False

        if len(exclude) > 0:
            _LOGGER.warning(
                "Unable to connect to the %s node. attempting to switch to the %s node",
                ",".join(self.ws_state.exclude_station),
                self.ws_state.station,
            )

        return self.ws_state.station


@dataclasses.dataclass
class CoordinatorConfig:
    """Manage Update Coordinator configuration."""

    fast_interval = timedelta(seconds=1)
    base_interval = timedelta(seconds=5)
    retrie_interval = timedelta(minutes=5)
    max_interval = timedelta(minutes=15)
    params = {}
    cached_eew_data = None
    store_eew: Store | None = None
    cached_report_data = None
    store_report: Store | None = None
    report_fetch_time = 0


@dataclasses.dataclass
class CoordinatorState:
    """Manage Update Coordinator State."""

    use_http_fallback = False
    station = None
    earthquake = {}
    simulating = {}
    intensity = {}
    report_data = {}
    rts_data = {}
    tsunami_data = {}


@dataclasses.dataclass
class CoordinatorTask:
    """Manage Update Coordinator Task."""

    initialize_task: Task | None = None
    retry_backoff = 1
    unsub_shutdown = None


class Trem2UpdateCoordinator(DataUpdateCoordinator):
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

        self.conf_manager = CoordinatorConfig()
        self.state_manager = CoordinatorState()
        self.task_manager = CoordinatorTask()
        self.http_manager = ExpTechHTTPManager()
        self.ws_manager = ExpTechWSManager()

        self.conf_manager.store_eew = store_eew
        self.conf_manager.store_report = store_report
        self.http_manager.session = async_get_clientsession(hass)

    async def _initialize(self) -> bool:
        """Initialize for fetching data."""
        self.update_interval = self.conf_manager.base_interval
        http_exclude = self.http_manager.exclude_station
        ws_exclude = self.ws_manager.ws_state.exclude_station
        config_options = self.config_entry.options

        # Disconnect websocket if running
        if self.ws_manager.ws_state.is_running:
            self.hass.async_add_executor_job(self.ws_manager.disconnect)

        # Setup config entry options to params
        provider = dict(PROVIDER_OPTIONS).get(
            config_options.get(CONF_PROVIDER),
        )
        if provider is not None:
            self.conf_manager.params["type"] = provider

        # Setup Http fetch method
        if bool(self.http_manager.station):
            http_exclude.append(self.http_manager.station)
        self.state_manager.station = await self.http_manager.initialize_route(exclude=http_exclude)

        # Setup WebSocket fetch method
        _api_token = config_options.get(CONF_API_TOKEN, "")
        if bool(_api_token):
            if bool(self.ws_manager.ws_state.station):
                ws_exclude.append(self.ws_manager.ws_state.station)
            self.state_manager.station = await self.ws_manager.initialize_route(exclude=ws_exclude)

            self.ws_manager.hass = self.hass
            self.ws_manager.ws_config.access_token = _api_token
            self.ws_manager.ws_config.params = self.conf_manager.params
            self.http_manager.websocket = self.hass.async_add_executor_job(
                self.ws_manager.connect,
            )

            self.update_interval = timedelta(seconds=1)

        # If max retries, raise connection failures
        if self.state_manager.station:
            unavailable = ws_exclude if bool(_api_token) else http_exclude
            await self.server_status_event(unavailable=unavailable)
        else:
            self.http_manager.station = None
            self.ws_manager.ws_state.station = None
            raise ConnectionRefusedError("ExpTech server connection failures")

    async def async_register_shutdown(self):
        """Register shutdown on HomeAssistant stop."""

        async def _on_hass_stop(event):
            await self.async_shutdown()

        self.task_manager.unsub_shutdown = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            _on_hass_stop,
        )

    async def async_shutdown(self):
        """Perform websocket disconnect."""
        if self.http_manager.websocket:
            self.hass.async_add_executor_job(self.ws_manager.disconnect)

    async def _async_update_data(self):
        """Poll earthquake data."""
        resp = None
        use_http_fetch = True

        # 初始化作業
        init_task = self.task_manager.initialize_task
        if init_task:
            # 完成後判斷是否錯誤
            if init_task.done() and bool(init_task.exception()):
                self.update_interval = self.conf_manager.retrie_interval
                raise UpdateFailed(init_task.exception())
        else:
            # 初始化開始
            self.task_manager.initialize_task = self.hass.async_create_task(
                self._initialize(),
                name="trem2_initializing",
            )
            self.task_manager.initialize_task.add_done_callback(
                self._log_task_exception,
            )
            return None

        # 優先使用 WebSocket 獲取資料
        if self.ws_manager.ws_state.is_running:
            try:
                # 需要重新登入
                if self.ws_manager.ws_state.credentials is None:
                    self.hass.async_add_executor_job(self.ws_manager.disconnect)
                    raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

                # 使用者未訂閱
                if not bool(self.ws_manager.ws_state.subscrib_service):
                    self.hass.async_add_executor_job(self.ws_manager.disconnect)
                    raise ConfigEntryAuthFailed("The ExpTech VIP has expired, Please re-subscribe.")

                # 取得已接收訊息並處理
                resp = await self._handle(await self.ws_manager.recv())
                use_http_fetch = False

                # 正常處理訊息，取消降級
                if self.state_manager.use_http_fallback:
                    self.state_manager.use_http_fallback = False
                    self.update_interval = self.conf_manager.fast_interval
                    await self.server_status_event()
                    _LOGGER.info("WebSocket fetching data recovered")

            except ConnectionResetError as ex:
                self.task_manager.initialize_task = None
                self.state_manager.use_http_fallback = True
                self.update_interval = self.conf_manager.base_interval
                await self.server_status_event()
                _LOGGER.info("WebSocket error: %s, falling back to HTTP", str(ex))
            except RuntimeError as ex:
                raise UpdateFailed(str(ex)) from ex

        # 透過 HTTP 獲取資料
        if use_http_fetch:
            try:
                _data = await self.http_manager.fetch_eew(self.conf_manager.params)
                resp = _data[0] if len(_data) > 0 else {}
            except RuntimeError:
                self.task_manager.initialize_task = None

        # 如果需要初始化，進入指數退避
        if self.task_manager.initialize_task is None:
            self.task_manager.retry_backoff = min(self.task_manager.retry_backoff * 2, 256)
            new_interval = min(
                self.conf_manager.base_interval * self.task_manager.retry_backoff,
                self.conf_manager.max_interval,
            )
            self.update_interval = new_interval
            raise UpdateFailed(f"Update failed, next attempt in {new_interval.total_seconds()} seconds")

        if self.task_manager.retry_backoff > 1:
            self.task_manager.retry_backoff = 1
            self.http_manager.exclude_station = []
            self.ws_manager.ws_state.exclude_station = []

        # 儲存速報及報告資訊
        self.state_manager.earthquake = await self._load_eew_data(
            resp,
            self.state_manager.simulating,
        )
        self.state_manager.report_data = await self._load_report_data(
            resp,
            self.state_manager.simulating,
        )

        return self._fulsh_cache

    async def _handle(self, resp: dict):
        """Handle incoming WebSocket messages based on type."""
        if resp is None:
            raise RuntimeError("An error occurred during message handling")

        event_type = resp.get("type")
        if event_type is None:
            return {}

        if event_type == "eew":
            eq_data: dict = resp.get("data", {})
            if bool(eq_data) and "time" not in eq_data:
                eq_data["time"] = resp.get("time", 0)

            return eq_data

        if event_type == "report":
            report_data: dict = resp.get("data", {})
            await self._save_report(report_data)

        if event_type == "intensity":
            int_data: dict = resp.get("data", {})
            self.state_manager.intensity = int_data
            _LOGGER.debug("Intensity data: %s", int_data)

        if event_type == "rts":
            rts_data: dict = resp.get("data", {})
            int_list = rts_data.get("int")

            self.state_manager.rts_data = {
                "box": rts_data.get("box"),
                "int": int_list,
            }

            if int_list is not None:
                _LOGGER.debug("RTS Data: %s", int_list)

        if event_type == "tsunami":
            tsunami_data: dict = resp.get("data", {})
            if bool(tsunami_data) and "time" not in tsunami_data:
                tsunami_data["time"] = resp.get("time", 0)

            self.state_manager.tsunami_data = tsunami_data
            _LOGGER.debug("Tsunami Data: %s", tsunami_data)

        return {}

    async def _load_eew_data(self, resp: dict, simulator: dict):
        """Fallback to store or update data."""
        try:
            # Case 1: if simulator data is not empty
            if "eq" in simulator:
                return simulator

            cached_eew = self.conf_manager.cached_eew_data
            store_eew = self.conf_manager.store_eew

            # Case 2: if response data is not empty
            if "id" in resp:
                if not self._data_equal(resp, cached_eew):
                    # Save the last data to the store
                    await store_eew.async_save(resp)
                    cached_eew = resp

                    self.hass.bus.fire(
                        f"{DOMAIN}_notification",
                        {"earthquake": str(resp)},
                        origin=EventOrigin.remote,
                    )
                    _LOGGER.debug("Earthquake data: %s", resp)

            # Case 3: if cached is empty, restore data from the store
            if cached_eew is None:
                store_data = await store_eew.async_load()
                cached_eew = store_data or {}
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing eew data: %s",
                str(ex),
            )

        return cached_eew

    async def _load_report_data(self, eq_data: dict, simulator: dict):
        """Fallback to report store or update data."""
        try:
            # if simulating earthquake, return empty report data
            if "id" in simulator:
                return {}

            # if report is empty, restore data from the store
            if self.conf_manager.cached_report_data is None:
                report_data = await self.conf_manager.store_report.async_load() or {}
            else:
                report_data = (
                    self.conf_manager.cached_report_data[0]
                    if isinstance(
                        self.conf_manager.cached_report_data,
                        list,
                    )
                    and len(self.conf_manager.cached_report_data) > 0
                    else self.conf_manager.cached_report_data
                )

            # Check data is up to date
            report_time = report_data.get("time", 0)
            eew_time = eq_data.get("time", 1)
            if eew_time > report_time:
                # Check if the report data is older than 5 minutes
                if abs(self.conf_manager.report_fetch_time - datetime.now().timestamp()) > 300:
                    # Execute fetching data from the report server
                    report_data = await self.http_manager.fetch_report(report_data)
                    await self._save_report(report_data)

            self.conf_manager.cached_report_data = report_data
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing report data: %s",
                str(ex),
            )

        return report_data

    async def _save_report(self, data):
        self.conf_manager.cached_report_data = data
        await self.conf_manager.store_report.async_save(data)
        self.conf_manager.report_fetch_time = datetime.now().timestamp()

        self.hass.bus.fire(
            f"{DOMAIN}_report",
            data,
            origin=EventOrigin.remote,
        )
        _LOGGER.debug("Report data: %s", data)

    async def server_status_event(self, **kwargs):
        """Server status update trigger event."""
        api_node = kwargs.get("station", self.state_manager.station)
        unavailable = kwargs.get("unavailable", [])
        protocol = await self.connection_status()

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
        _LOGGER.debug(event_data)

    async def connection_status(self) -> str:
        """Return current connection mode."""
        if self.ws_manager.ws_state.is_running:
            return "http (fallback)" if self.state_manager.use_http_fallback else "websocket"

        return "http"

    def _fulsh_cache(self):
        if sys.getsizeof(self.conf_manager.cached_eew_data) > 1e6:
            self.conf_manager.cached_eew_data = None
        if sys.getsizeof(self.conf_manager.cached_report_data) > 1e6:
            self.conf_manager.cached_report_data = None

        return self

    @staticmethod
    def _log_task_exception(task: Task):
        if task.cancelled():
            _LOGGER.debug("Background task was cancelled (Home Assistant is stopping)")
            return

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            _LOGGER.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
            return

        if exc:
            _LOGGER.error("Initialize task failed: %s", exc, exc_info=exc)

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
