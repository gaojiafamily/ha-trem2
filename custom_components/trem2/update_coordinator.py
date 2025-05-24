"""Common Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging
from typing import TYPE_CHECKING

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.http import ExpTechHTTPClient
from .api.websocket import ExpTechWSClient
from .const import DOMAIN, PARAMS_OPTIONS, PROVIDER_OPTIONS
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from .data_classes import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


@dataclass
class ExpTechClient:
    """Class to help client threads."""

    http: ExpTechHTTPClient
    websocket: ExpTechWSClient


@dataclass
class Trem2Conf:
    """Class for save the TREM state retrieval."""

    fast_interval = timedelta(seconds=1)
    base_interval = timedelta(seconds=5)
    retrie_interval = timedelta(minutes=5)
    max_interval = timedelta(minutes=15)
    params = {}


@dataclass
class Trem2State:
    """Class for save the TREM state retrieval."""

    # initialization
    api_node: str | None = None
    retry_backoff = 1
    use_http_fallback = False
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
        config_entry: Trem2ConfigEntry,
    ) -> None:
        """Initialize the Data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=config_entry.title,
        )

        # Get client session
        session = async_get_clientsession(hass)

        # Coordinator initialization
        self.client = ExpTechClient(
            http=ExpTechHTTPClient(
                session,
                _LOGGER,
            ),
            websocket=ExpTechWSClient(
                hass,
                session,
                _LOGGER,
            ),
        )
        self.config_entry = config_entry
        self.conf = Trem2Conf()
        self.session = session
        self.state = Trem2State()

    async def _initialize(self, http_exclude: list, ws_exclude: list):
        """Re-initialize the HTTP and WebSocket clients."""
        try:
            if self.client.http.api_node:
                http_exclude.append(self.client.http.api_node)
            self.client.http.initialize_route(
                action="service",
                unavailable=http_exclude,
            )

            if self.client.websocket.api_node:
                ws_exclude.append(self.client.websocket.api_node)
            self.client.websocket.initialize_route(
                action="service",
                unavailable=ws_exclude,
            )

            # Disconnect websocket if running
            if self.client.websocket.state.is_running:
                await self.client.websocket.disconnect()
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

        # Setup WebSocket or HTTP fetch method
        _api_token = config_options.get(CONF_API_TOKEN)
        if _api_token:
            try:
                self.client.websocket.conf.access_token = _api_token
                self.client.websocket.conf.params = self.conf.params
                await self.client.websocket.connect()
                self.state.update_interval = self.conf.fast_interval
                self.state.api_node = self.client.websocket.api_node
            except RuntimeError as ex:
                raise ConfigEntryNotReady(f"{ex!r}") from ex
        else:
            self.client.http.params = self.conf.params
            report_data = await self.client.http.fetch_report()
            await self._save_report(
                self.config_entry.runtime_data.report_store,
                report_data,
            )
            self.state.update_interval = self.conf.base_interval
            self.state.api_node = self.client.http.api_node

        # If max retries, raise connection failures
        self.update_interval = self.state.update_interval
        unavailable = self.client.websocket.unavailables if _api_token else self.client.http.unavailables
        if self.state.api_node:
            self.state.retry_backoff = 1
            self.server_status_event(
                event_fire=True,
                unavailable=unavailable,
            )
        else:
            self.client.http.api_node = None
            self.client.websocket.api_node = None
            self.logger.error(
                "No available nodes (%s), the service will be suspended",
                ",".join(unavailable),
            )
            raise ConfigEntryNotReady("ExpTech server connection failures")

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
        if self.client.websocket.state.is_running:
            await self.client.websocket.disconnect()

    async def _async_update_data(self):
        """Perform update data."""
        resp = None
        use_http_fetch = True

        # Fetch data from WebSocket
        if self.client.websocket.state.is_running and self.client.websocket.state.subscrib_service:
            resp = await self._websocket_update_data(self.client.websocket.state.subscrib_service)
            use_http_fetch = self.state.use_http_fallback

        # Fetch data from http
        if use_http_fetch:
            try:
                resp = await self.client.http.fetch_eew()
            except RuntimeError:
                self.state.retry_backoff += 1

        # Reset retry backoff if data is received
        if resp is not None:
            self.state.retry_backoff = 1

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
                raise ConfigEntryNotReady("The ExpTech server is not responding")
            case retries if retries > 1:
                new_interval = min(
                    self.conf.base_interval * self.state.retry_backoff,
                    self.conf.max_interval,
                )
                self.update_interval = new_interval
                _LOGGER.error(f"Update failed, next attempt in {new_interval.total_seconds()} seconds")
                raise UpdateFailed()

    async def _websocket_update_data(self, subscrib_service: list):
        """Perform WebSocket update data."""
        try:
            # If re-auth is required, an exception is raised
            if self.client.websocket.state.credentials is None:
                await self.client.websocket.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

            # If re-subscribe is required, an exception is raised
            if len(subscrib_service) == 0:
                await self.client.websocket.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP has expired, Please re-subscribe.")

            # Handle incoming WebSocket messages
            resp = await self._handle(await self.client.websocket.recv())

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
                node=self.client.http.api_node,
                unavailable=self.client.websocket.api_node,
            )
            self.state.retry_backoff += 1
            _LOGGER.warning("WebSocket error: %s, falling back to HTTP", str(ex))

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
            store_eew: Store = self.config_entry.runtime_data.recent_sotre

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
            store_report: Store = self.config_entry.runtime_data.report_store
            if self.state.cache_report is None:
                report_data = await store_report.async_load() or {}
            else:
                report_data = self.state.cache_report

            # Check data is up to date
            report_time = report_data.get("time", 0)
            eew_time = eq_data.get("time", 1)
            if eew_time > report_time:
                # Check if the report data is older than 5 minutes
                if abs(self.state.report_fetch_time - datetime.now().timestamp()) > 300:
                    # Execute fetching data from the report server
                    self.state.cache_report = await self.client.http.fetch_report(report_data)
                    await self._save_report(store_report, self.state.cache_report)
            else:
                self.state.cache_report = report_data
        except (AttributeError, TypeError, RuntimeError) as ex:
            _LOGGER.error(
                "An exception occurred while accessing report data: %s",
                str(ex),
            )

        return self.state.cache_report

    async def _save_report(self, stored: Store, data: dict | None = None):
        """Save report store to store."""
        self.state.cache_report = data
        await stored.async_save(data)
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
            (self.client.websocket if self.client.websocket.state.is_running else self.client.http).api_node,
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
        if self.client.websocket.state.is_running:
            return "http (fallback)" if self.state.use_http_fallback else "websocket"

        return "http"

    def _connection_latency(self) -> float | str:
        """Return current latency."""
        update_interval = self.state.update_interval.total_seconds()
        latency = self.client.http.latency + (update_interval if update_interval > 1 else 0)
        if self.client.websocket.state.is_running and not self.state.use_http_fallback:
            latency = abs(
                self.client.websocket.state.ping_time - self.client.websocket.state.pong_time,
            )

        return f"{latency:.3f}" if latency < 6 else "6s+"

    @staticmethod
    def _data_equal(a, b):
        """Comparison of data structures."""
        if not all((a, b)):
            return False

        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
