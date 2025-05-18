"""Common Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging

from aiohttp import WSServerHandshakeError
from dataclasses import dataclass

from homeassistant.const import CONF_API_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
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
        self.store_eew = Store(hass, 1, STORAGE_EEW)
        self.store_report = Store(hass, 1, STORAGE_REPORT)
        self.params = {}


@dataclass
class Trem2State:
    """Class for save the TREM state retrieval."""

    # initialization
    api_node: str | None = None
    retry_backoff = 1
    use_http_fallback = False
    reinitialize = False
    update_interval = timedelta(seconds=5)

    # Sensor state
    cache_eew: list | None = None
    earthquake: dict | None = None
    simulating = {}
    cache_report: dict | None = None
    report: dict | None = None
    report_fetch_time: float = 0
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

    async def _initialize(self, http_exclude: list, ws_exclude: list):
        """Re-initialize the HTTP and WebSocket clients."""
        try:
            if self.http_client.api_node:
                http_exclude.append(self.http_client.api_node)
            self.http_client.initialize_route(
                action="service",
                unavailable=http_exclude,
            )

            if self.ws_client.api_node:
                ws_exclude.append(self.ws_client.api_node)
            self.ws_client.initialize_route(
                action="service",
                unavailable=ws_exclude,
            )

            # Disconnect websocket if running
            if self.ws_client.state.is_running:
                await self.ws_client.disconnect()
        except RuntimeError as ex:
            raise ConfigEntryError(f"{ex!r}") from ex

    async def _async_setup(self):
        """Perform initialize client."""

        def get_provider_option(key, val):
            if key == "type":
                for k, v in PROVIDER_OPTIONS:
                    if k == val:
                        return v
            return val

        # Setup config entry options to params
        config_options = getattr(self.config_entry, "options", {})
        self.conf.params = {
            k: get_provider_option(k, v) for k, v in config_options.items() if k in PARAMS_OPTIONS and v
        }

        # Re-initialize
        http_exclude = self.http_client.unavailables
        ws_exclude = self.ws_client.unavailables
        if self.state.reinitialize:
            await self._initialize(http_exclude, ws_exclude)

        # Setup WebSocket or HTTP fetch method
        _api_token = config_options.get(CONF_API_TOKEN)
        if _api_token:
            try:
                self.ws_client.conf.access_token = _api_token
                self.ws_client.conf.params = self.conf.params
                await self.ws_client.connect()
                self.state.update_interval = self.conf.fast_interval
                self.state.api_node = self.ws_client.api_node
            except RuntimeError:
                self.state.reinitialize = True
                return
            except WSServerHandshakeError as ex:
                if ex.status == 502:
                    self.state.reinitialize = True
                    return
        else:
            self.http_client.params = self.conf.params
            report_data = await self.http_client.fetch_report()
            await self._save_report(report_data)
            self.state.update_interval = self.conf.base_interval
            self.state.api_node = self.http_client.api_node

        # If max retries, raise connection failures
        self.update_interval = self.state.update_interval
        unavailable = ws_exclude if _api_token else http_exclude
        if self.state.api_node:
            self.state.reinitialize = False
            self.state.retry_backoff = 1
            self.server_status_event(
                event_fire=True,
                unavailable=unavailable,
            )
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
            await self._async_shutdown()

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            _on_hass_stop,
        )

    async def _async_shutdown(self):
        """Perform WebSocket disconnect."""
        if self.ws_client.state.is_running:
            await self.ws_client.disconnect()

    async def _async_update_data(self):
        """Perform update data."""
        resp = None
        use_http_fetch = True

        # re-initialize client if needed
        if self.state.reinitialize:
            await self._async_setup()

        # Fetch data from WebSocket
        if self.ws_client.state.is_running and self.ws_client.state.subscrib_service:
            resp = await self._websocket_update_data(self.ws_client.state.subscrib_service)
            use_http_fetch = self.state.use_http_fallback

        # Fetch data from http
        if use_http_fetch:
            try:
                resp = await self.http_client.fetch_eew()
            except RuntimeError:
                self.state.retry_backoff = min(self.state.retry_backoff * 2, 256)

        # Storing earthquake and report data
        self.state.earthquake = await self._load_eew_data(
            resp,
            self.state.simulating,
        )
        self.state.report = await self._load_report_data(
            self.state.earthquake,
            self.state.simulating,
        )

        # Retry backoff if no data
        match self.state.retry_backoff:
            case retries if retries >= 5:
                self.state.reinitialize = True
            case retries if retries > 1:
                new_interval = min(
                    self.conf.base_interval * self.state.retry_backoff,
                    self.conf.max_interval,
                )
                self.update_interval = new_interval
                raise UpdateFailed(f"Update failed, next attempt in {new_interval.total_seconds()} seconds")

    async def _websocket_update_data(self, subscrib_service: list):
        """Perform WebSocket update data."""
        try:
            # If re-auth is required, an exception is raised
            if self.ws_client.state.credentials is None:
                await self.ws_client.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

            # If re-subscribe is required, an exception is raised
            if len(subscrib_service) == 0:
                await self.ws_client.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP has expired, Please re-subscribe.")

            # Handle incoming WebSocket messages
            resp = await self._handle(await self.ws_client.recv())

            # Cancel the http fetch if WebSocket is running
            if self.state.use_http_fallback:
                self.state.use_http_fallback = False
                self.update_interval = self.conf.fast_interval
                self.server_status_event(
                    event_fire=True,
                )
                _LOGGER.info("WebSocket fetching data recovered")

            # Return the response
            return resp

        except (ConnectionError, RuntimeError) as ex:
            self.state.use_http_fallback = True
            self.server_status_event(
                event_fire=self.state.retry_backoff == 1,
                node=self.http_client.api_node,
                unavailable=self.ws_client.api_node,
            )
            self.state.retry_backoff = min(self.state.retry_backoff * 2, 256)
            _LOGGER.info("WebSocket error: %s, falling back to HTTP", str(ex))

    async def _handle(self, resp: dict | None) -> list:
        """Handle incoming WebSocket messages based on type."""
        if resp is None:
            raise RuntimeError("An error occurred during message handling")

        event_type = resp.get("type")
        match event_type:
            case "eew":
                eq_data: dict = resp.get("data", {})
                eq_data.pop("type", None)
                eq_data.setdefault("time", resp.get("time", 0))

                return [eq_data]

            case "report":
                report_data = resp.get("data", {})
                await self._save_report(report_data)

            case "intensity":
                int_data = resp.get("data", {})
                self.state.intensity = int_data
                _LOGGER.debug("Intensity data: %s", int_data)

            case "tsunami":
                tsunami_data: dict = resp.get("data", {})
                tsunami_data.setdefault("time", resp.get("time", 0))
                self.state.tsunami = tsunami_data
                _LOGGER.debug("Tsunami Data: %s", tsunami_data)

        return []

    async def _load_eew_data(self, resp: list | None, simulator: dict) -> dict:
        """Fallback to store or update data."""
        try:
            # Case 1: if simulator data is not empty
            if "eq" in simulator:
                return simulator

            cached_eew = self.state.cache_eew
            store_eew = self.conf.store_eew

            # Case 2: if response data is not empty
            if resp:
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
                cached_eew = store_data or []
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing eew data: %s",
                str(ex),
            )

        if isinstance(cached_eew, list) and len(cached_eew) > 0:
            filtered = [d for d in cached_eew if d.get("author") == "cwa"]
            return filtered[0] if filtered else cached_eew[0]

        return {}

    async def _load_report_data(self, eq_data: dict, simulator: dict) -> dict | None:
        """Fallback to report store or update data."""
        try:
            # if simulating earthquake, return empty report data
            if "id" in simulator:
                return {}

            # if report is empty, restore data from the store
            if self.state.cache_report is None:
                report_data = await self.conf.store_report.async_load() or {}
            else:
                report_data = self.state.cache_report

            # Check data is up to date
            report_time = report_data.get("time", 0)
            eew_time = eq_data.get("time", 1)
            if eew_time > report_time:
                # Check if the report data is older than 5 minutes
                if abs(self.state.report_fetch_time - datetime.now().timestamp()) > 300:
                    # Execute fetching data from the report server
                    self.state.cache_report = await self.http_client.fetch_report(report_data)
                    await self._save_report(self.state.cache_report)
            else:
                self.state.cache_report = report_data
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing report data: %s",
                str(ex),
            )

        return self.state.cache_report

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

    def server_status_event(self, **kwargs):
        """Server status update trigger event."""
        server_status = self.server_status(**kwargs)

        event_data = {
            "type": "server_status",
            "protocol": self.connection_status(),
        }
        event_data.update(server_status)

        _LOGGER.info(event_data)
        self.hass.bus.fire(
            f"{DOMAIN}_status",
            event_data,
        )

    def server_status(self, **kwargs):
        """Return current server status."""
        self.state.api_node = kwargs.get(
            "node",
            (self.ws_client if self.ws_client.state.is_running else self.http_client).api_node,
        )
        if self.update_interval:
            self.state.update_interval = self.update_interval

        return {
            "current_node": self.state.api_node,
            "unavailable": kwargs.get("unavailable", []),
            "latency": self._connection_latency(),
        }

    def connection_status(self) -> str:
        """Return current connection mode."""
        if self.ws_client.state.is_running:
            return "http (fallback)" if self.state.use_http_fallback else "websocket"

        return "http"

    def _connection_latency(self) -> float | str:
        """Return current latency."""
        update_interval = self.state.update_interval.total_seconds()
        latency = self.http_client.latency + (update_interval if update_interval > 1 else 0)
        if self.ws_client.state.is_running and not self.state.use_http_fallback:
            latency = abs(
                self.ws_client.state.ping_time - self.ws_client.state.pong_time,
            )

        return f"{latency:.3f}" if latency < 6 else "6s+"

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
