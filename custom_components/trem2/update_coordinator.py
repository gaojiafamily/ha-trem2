"""Common Data for TREM2 component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.http import ExpTechHTTPClient
from .api.websocket import ExpTechWSClient
from .const import DOMAIN, PARAMS_OPTIONS, PROVIDER_OPTIONS
from .runtime import ExpTechClient, ExpTechConf
from .store import Trem2Store

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


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
            always_update=False,
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
                config_entry,
                hass,
                session,
            ),
        )
        self.config_entry = config_entry
        self.conf = ExpTechConf()
        self.session = session
        self.store = Trem2Store(
            hass,
            _LOGGER,
            config_entry,
        )

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
                self.client.update_interval = self.conf.fast_interval
            except RuntimeError as ex:
                raise ConfigEntryNotReady from ex
        else:
            self.client.http.params = self.conf.params
            self.client.update_interval = self.conf.base_interval

        # Setup coordinator data
        await self.store.load_recent_data()
        await self.store.load_report_data()
        await self.store.fetch_report()

        # If max retries, raise connection failures
        self.update_interval = self.client.update_interval
        unavailable = (self.client.websocket if _api_token else self.client.http).unavailables
        _, api_node = await self.client.api_node()
        if api_node:
            self.client.retry_backoff = 1
            await self.server_status_event(
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

        await self.async_register_shutdown()

    async def async_register_shutdown(self):
        """Register shutdown on HomeAssistant stop."""

        async def _on_hass_stop(event):
            await self._async_shutdown()

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            _on_hass_stop,
        )

    async def _async_shutdown(self):
        """Perform WebSocket disconnect and data saving."""
        if self.client.websocket.state.is_running:
            await self.client.websocket.disconnect()

        await self.config_entry.runtime_data.recent_sotre.async_save(
            self.store.coordinator_data["recent"],
        )
        await self.config_entry.runtime_data.report_store.async_save(
            self.store.coordinator_data["report"],
        )

    async def _async_update_data(self):
        """Perform update data."""
        flag = None
        use_http_fetch = True

        # Fetch data from WebSocket
        ws_state = self.client.websocket.state
        if ws_state.is_running and ws_state.subscrib_service:
            flag = await self._websocket_update_data(ws_state.subscrib_service)
            self.client.retry_backoff = 1 if flag else self.client.retry_backoff + 1
            use_http_fetch = self.client.use_http_fallback

        # Fetch data from http
        if use_http_fetch:
            flag = await self._http_update_data()
            self.client.retry_backoff = 1 if flag else self.client.retry_backoff + 1

        # Retry backoff if no data
        match self.client.retry_backoff:
            case retries if retries >= 10:
                hass = self.hass
                entry_id = self.config_entry.entry_id
                hass.async_create_task(hass.config_entries.async_reload(entry_id))
                raise HomeAssistantError("The ExpTech server is not responding")
            case retries if retries > 1:
                new_interval = min(
                    self.conf.base_interval * self.client.retry_backoff,
                    self.conf.max_interval,
                )
                self.update_interval = new_interval
                _LOGGER.error(
                    "Update failed, next attempt in %s seconds",
                    new_interval.total_seconds(),
                )
                raise UpdateFailed

        return self.store.coordinator_data

    async def _http_update_data(self) -> bool:
        """Preform Http update data."""
        try:
            # Handle incoming Http messages
            resp = await self.client.http.fetch_eew()
            if resp:
                # Provider preferred CWA
                filtered = [d for d in resp if d.get("author") == "cwa"]
                await self._handle({
                    "type": "eew",
                    "data": filtered[0] if filtered else resp[0],
                })

        except RuntimeError:
            self.client.retry_backoff += 1
            return False

        return True

    async def _websocket_update_data(self, subscrib_service: list) -> bool:
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
            resp = await self.client.websocket.recv()
            await self._handle(resp)

            # Cancel the http fetch if WebSocket is running
            if self.client.use_http_fallback:
                self.client.use_http_fallback = False
                self.update_interval = self.conf.fast_interval
                await self.server_status_event(
                    event_fire=True,
                )
                _LOGGER.info("WebSocket fetching data recovered")

        except (ConnectionError, RuntimeError) as ex:
            self.client.use_http_fallback = True
            await self.server_status_event(
                event_fire=self.client.retry_backoff == 1,
                node=self.client.http.api_node,
                unavailable=self.client.websocket.api_node,
            )
            self.client.retry_backoff += 1
            _LOGGER.warning("WebSocket error: %s, falling back to HTTP", str(ex))
            return False

        return True

    async def _handle(self, resp: dict[str, Any]) -> None:
        """Handle incoming WebSocket messages based on type."""
        event_type = resp.get("type")

        # Handled message on type
        match event_type:
            case "eew":
                data: dict[str, Any] = resp.get("data", {})
                flag = await self.store.load_recent_data(data)

                # Event bus fired
                if flag:
                    self.hass.bus.fire(
                        f"{DOMAIN}_notification",
                        {"earthquake": data},
                        origin=EventOrigin.remote,
                    )

            case "report":
                data: dict[str, Any] = resp.get("data", {})
                flag = await self.store.load_report_data(data)

                # Event bus fired
                if flag:
                    self.hass.bus.fire(
                        f"{DOMAIN}_report",
                        {"earthquake": data},
                        origin=EventOrigin.remote,
                    )

            case "intensity":
                resp.pop("type", None)
                self.store.coordinator_data["recent"]["intensity"] = resp
                _LOGGER.debug("Intensity data: %s", resp)

            case "tsunami":
                tsunami_data: dict = resp.get("data", {})
                tsunami_data.setdefault("time", resp.get("time", 0))
                self.store.coordinator_data["recent"]["tsunami"] = tsunami_data
                _LOGGER.debug("Tsunami Data: %s", tsunami_data)

    async def server_status_event(self, **kwargs):
        """Server status update trigger event."""
        server_status = await self.client.server_status(**kwargs)
        protocol, _ = await self.client.api_node()

        event_data = {
            "type": "server_status",
            "protocol": protocol,
        }
        event_data.update(server_status)

        _LOGGER.info(event_data)
        self.hass.bus.fire(
            f"{DOMAIN}_status",
            event_data,
        )
