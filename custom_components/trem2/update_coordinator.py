"""Common Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging

from dataclasses import dataclass

from homeassistant.const import CONF_API_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.http import ExpTechHTTPClient
from .api.websocket import ExpTechWSClient
from .const import DOMAIN, STORAGE_EEW, STORAGE_REPORT, PARAMS_OPTIONS, PROVIDER_OPTIONS

_LOGGER = logging.getLogger(__name__)


class Trem2Conf:
    """Class for save the TREM state retrieval."""

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Coordinator configuration."""
        self.fast_interval = timedelta(seconds=1)
        self.base_interval = timedelta(seconds=5)
        self.retrie_interval = timedelta(minutes=5)
        self.max_interval = timedelta(minutes=15)
        self.store_eew = Store(hass, 2, STORAGE_EEW)
        self.store_report = Store(hass, 1, STORAGE_REPORT)
        self.params = {}


@dataclass
class Trem2State:
    """Class for save the TREM state retrieval."""

    # initialization
    api_node = None
    retry_backoff = 1
    use_http_fallback = False
    reinitialize = False
    update_interval = timedelta(seconds=5)
    unsub_shutdown = None

    # Sensor state
    cache_eew = {}
    earthquake = {}
    simulating = {}
    cache_report = {}
    report = {}
    report_fetch_time = 0
    intensity = {}
    rts = {}
    tsunami = {}


class Trem2UpdateCoordinator(DataUpdateCoordinator):
    """Class for handling the TREM data retrieval."""

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )

        # Coordinator initialization
        self.conf = Trem2Conf(hass)
        self.state = Trem2State()
        self.session = async_get_clientsession(hass)
        self.http_client = ExpTechHTTPClient(
            self.session,
            _LOGGER,
        )
        self.ws_client = ExpTechWSClient(
            hass,
            self.session,
            _LOGGER,
        )

    async def _async_setup(self):
        """Perform initialize client."""

        def get_provider_option(key, val):
            if key == "type":
                for k, v in PROVIDER_OPTIONS:
                    if k == val:
                        return v
            return val

        self.update_interval = self.state.update_interval
        config_options = self.config_entry.options
        http_exclude = self.http_client.unavailables
        ws_exclude = self.ws_client.unavailables

        # Disconnect websocket if running
        if self.ws_client.state.is_running:
            await self.ws_client.disconnect()

        # Setup config entry options to params
        config_options = self.config_entry.options
        self.conf.params = {
            k: get_provider_option(k, v)
            for k, v in config_options.items()
            if k in PARAMS_OPTIONS and v
        }

        # Setup Http fetch method
        if self.http_client.api_node:
            http_exclude.append(self.http_client.api_node)
        self.state.api_node = self.http_client.initialize_route(
            unavailable=http_exclude,
        )
        self.http_client.params = self.conf.params
        self.state.update_interval = self.conf.base_interval

        # Setup WebSocket fetch method
        _api_token = config_options.get(CONF_API_TOKEN)
        if _api_token:
            if self.ws_client.api_node:
                ws_exclude.append(self.ws_client.api_node)
            self.state.api_node = self.ws_client.initialize_route(
                unavailable=ws_exclude,
            )

            self.ws_client.conf.access_token = _api_token
            self.ws_client.conf.params = self.conf.params
            await self.ws_client.connect()
            self.state.update_interval = self.conf.fast_interval

        # If max retries, raise connection failures
        unavailable = ws_exclude if _api_token else http_exclude
        if self.state.api_node:
            self.update_interval = self.state.update_interval
            self.state.reinitialize = False
            await self.server_status_event(unavailable=unavailable)
        else:
            self.http_client.api_node = None
            self.ws_client.api_node = None
            self.logger.error(
                "No available nodes (%s), the service will be suspended",
                ",".join(unavailable),
            )
            raise ConnectionRefusedError("ExpTech server connection failures")

    async def async_register_shutdown(self):
        """Register shutdown on HomeAssistant stop."""

        async def _on_hass_stop(event):
            await self.async_shutdown()

        self.state.unsub_shutdown = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            _on_hass_stop,
        )

    async def async_shutdown(self):
        """Perform WebSocket disconnect."""
        if self.ws_client.state.is_running:
            await self.ws_client.disconnect()

    async def _async_update_data(self):
        """Perform update data."""
        resp = None
        use_http_fetch = True

        # 重新初始化客戶端
        if self.state.reinitialize:
            await self._async_setup

        # 優先使用 WebSocket 獲取資料
        if self.ws_client.state.is_running and self.ws_client.state.subscrib_service:
            try:
                # 需要重新登入
                if self.ws_client.state.credentials is None:
                    await self.ws_client.disconnect()
                    raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

                # 使用者未訂閱
                if len(self.ws_client.state.subscrib_service) == 0:
                    await self.ws_client.disconnect()
                    raise ConfigEntryAuthFailed(
                        "The ExpTech VIP has expired, Please re-subscribe."
                    )

                # 取得已接收訊息並處理
                resp = await self._handle(await self.ws_client.recv())
                use_http_fetch = False

                # 正常處理訊息，取消降級
                if self.state.use_http_fallback:
                    self.state.use_http_fallback = False
                    self.update_interval = self.conf.fast_interval
                    await self.server_status_event()
                    _LOGGER.info("WebSocket fetching data recovered")

            except ConnectionResetError as ex:
                self.state.reinitialize = True
                self.state.use_http_fallback = True
                await self.server_status_event()
                _LOGGER.info("WebSocket error: %s, falling back to HTTP", str(ex))
            except RuntimeError as ex:
                raise UpdateFailed(str(ex)) from ex

        # 透過 HTTP 獲取資料
        if use_http_fetch:
            try:
                _data = await self.http_client.fetch_eew()
                resp = _data[0] if len(_data) > 0 else {}
            except RuntimeError:
                self.state.reinitialize = True

        # 儲存速報及報告資訊
        self.state.earthquake = await self._load_eew_data(
            resp,
            self.state.simulating,
        )
        self.state.report = await self._load_report_data(
            resp,
            self.state.simulating,
        )

        # 如果需要初始化，進入指數退避
        if self.state.reinitialize:
            self.state.retry_backoff = min(self.state.retry_backoff * 2, 256)
            new_interval = min(
                self.conf.base_interval * self.state.retry_backoff,
                self.conf.max_interval,
            )
            self.state.update_interval = new_interval
            raise UpdateFailed(
                f"Update failed, next attempt in {new_interval.total_seconds()} seconds",
            )
        else:
            self.state.retry_backoff = 1
            self.http_client.unavailables = []
            self.ws_client.unavailables = []

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
            self.state.intensity = int_data
            _LOGGER.debug("Intensity data: %s", int_data)

        if event_type == "rts":
            rts_data: dict = resp.get("data", {})
            int_list = rts_data.get("int")

            self.state.rts = {
                "box": rts_data.get("box"),
                "int": int_list,
            }

            if int_list is not None:
                _LOGGER.debug("RTS Data: %s", int_list)

        if event_type == "tsunami":
            tsunami_data: dict = resp.get("data", {})
            if bool(tsunami_data) and "time" not in tsunami_data:
                tsunami_data["time"] = resp.get("time", 0)

            self.state.tsunami = tsunami_data
            _LOGGER.debug("Tsunami Data: %s", tsunami_data)

        return {}

    async def _load_eew_data(self, resp: dict, simulator: dict):
        """Fallback to store or update data."""
        try:
            # Case 1: if simulator data is not empty
            if "eq" in simulator:
                return simulator

            cached_eew = self.state.cache_eew
            store_eew = self.conf.store_eew

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
            if self.state.cache_report is None:
                report_data = await self.conf.store_report.async_load() or {}
            else:
                report_data = (
                    self.state.cache_report[0]
                    if isinstance(
                        self.state.cache_report,
                        list,
                    )
                    and len(self.state.cache_report) > 0
                    else self.state.cache_report
                )

            # Check data is up to date
            report_time = report_data.get("time", 0)
            eew_time = eq_data.get("time", 1)
            if eew_time > report_time:
                # Check if the report data is older than 5 minutes
                if abs(self.state.report_fetch_time - datetime.now().timestamp()) > 300:
                    # Execute fetching data from the report server
                    report_data = await self.http_client.fetch_report(report_data)
                    await self._save_report(report_data)

            self.state.cache_report = report_data
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing report data: %s",
                str(ex),
            )

    async def _save_report(self, data):
        """Save report store to store."""
        self.state.cache_report = data
        await self.conf.store_report.async_save(data)
        self.state.report_fetch_time = datetime.now().timestamp()

        self.hass.bus.fire(
            f"{DOMAIN}_report",
            data,
            origin=EventOrigin.remote,
        )
        _LOGGER.debug("Report data: %s", data)

    async def server_status_event(self, **kwargs):
        """Server status update trigger event."""
        api_node = kwargs.get("station", self.state.api_node)
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
        return "websocket" if self.ws_client.state.is_running else "http (fallback)"

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
