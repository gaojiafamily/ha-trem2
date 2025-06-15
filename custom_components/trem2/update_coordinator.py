"""Common Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_INTERVAL, DOMAIN, MAX_INTERVAL
from .data_client import Trem2DataClient

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

        self.config_entry = config_entry
        self.data_client = Trem2DataClient(
            hass,
            config_entry,
        )

    async def _async_setup(self):
        """Register shutdown on HomeAssistant stop."""

        async def _on_hass_stop(event):
            await self._async_shutdown()

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            _on_hass_stop,
        )

    async def _async_shutdown(self):
        """Perform WebSocket disconnect and data saving."""
        runtime_data = self.config_entry.runtime_data

        if self.web_socket and self.web_socket.state.is_running:
            await self.web_socket.disconnect()

        renect_store = runtime_data.sotre_handler.get_store("recent")
        await renect_store.async_save(
            self.data["recent"],
        )
        report_store = runtime_data.sotre_handler.get_store("report")
        await report_store.async_save(
            self.data["report"],
        )

    async def _async_update_data(self):
        """Perform update data."""
        flag = None
        use_http_fetch = True

        # Fetch data from WebSocket
        if self.web_socket and self.websocket_is_online():
            flag = await self._websocket_update_data(self.web_socket.state.subscrib_service)
            self.web_socket.retry_backoff = 0 if flag else self.web_socket.retry_backoff + 1
            use_http_fetch = self.web_socket.fallback_mode

        # Fetch data from http
        if use_http_fetch:
            flag = await self._http_update_data()
            self.http_client.retry_backoff = 0 if flag else self.http_client.retry_backoff + 1

        # Retry backoff if is not responding
        if self.http_client.retry_backoff >= 10 or (self.web_socket and self.web_socket.retry_backoff >= 10):
            hass = self.hass
            entry_id = self.config_entry.entry_id
            hass.async_create_task(hass.config_entries.async_reload(entry_id))
            raise HomeAssistantError("The ExpTech server is not responding")

        if self.http_client.retry_backoff > 0:
            self.retry_backoff(self.http_client.retry_backoff)
            self.http_client.unavailables.append(self.http_client.api_node)
            await self.http_client.initialize_route()

        if self.web_socket and self.web_socket.retry_backoff > 0:
            self.retry_backoff(self.web_socket.retry_backoff)
            self.web_socket.unavailables.append(self.web_socket.api_node)
            await self.web_socket.initialize_route()

        # Fetch report data
        if self.config_entry.runtime_data.fetch_report:
            await self._report_update_data()

        return self.data

    async def _report_update_data(self):
        """Fetch Report data."""
        fetch_report_flag = abs(datetime.now().timestamp() - self.data["report"]["fetch_time"]) < 600

        if fetch_report_flag:
            return

        report_data = await self.http_client.fetch_report(limit=1)
        cache: list[dict[str, Any]] = self.data["recent"]["cache"]
        seen = {d["id"] for d in cache}
        if report_data[0]["id"] in seen:
            await self.data_client.fetch_report()
            self.config_entry.runtime_data.fetch_report = False

    async def _http_update_data(self) -> bool:
        """Preform Http update data."""
        params = {}

        try:
            # Handle incoming Http messages
            resp = await self.http_client.fetch_eew()
            if resp:
                # Provider preferred CWA
                filtered = [d for d in resp if d.get("author") == "cwa"]
                if filtered:
                    self.config_entry.runtime_data.fetch_report = True
                    params = {"type": "eew", "data": filtered[0]}
                else:
                    params = {"type": "eew", "data": resp[0]}

                await self._handle(params)

        except RuntimeError:
            self.http_client.retry_backoff += 1
            return False

        self.update_interval = self.config_entry.runtime_data.update_interval
        return True

    async def _websocket_update_data(self, subscrib_service: list | None = None) -> bool:
        """Perform WebSocket update data."""
        if self.web_socket is None:
            return False

        if subscrib_service is None:
            subscrib_service = []

        try:
            # If re-auth is required, an exception is raised
            if self.web_socket.state.credentials is None:
                await self.web_socket.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP require re-auth.")

            # If re-subscribe is required, an exception is raised
            if len(subscrib_service) == 0:
                await self.web_socket.disconnect()
                raise ConfigEntryAuthFailed("The ExpTech VIP has expired, Please re-subscribe.")

            # Handle incoming WebSocket messages
            resp = await self.web_socket.recv()
            await self._handle(resp)

            # Cancel the http fetch if WebSocket is running
            if self.web_socket.fallback_mode:
                self.web_socket.fallback_mode = False
                self.update_interval = self.config_entry.runtime_data.update_interval
                await self.server_status_event(
                    event_fire=True,
                )
                _LOGGER.info("WebSocket fetching data recovered")

        except (ConnectionError, RuntimeError) as ex:
            self.web_socket.fallback_mode = True
            await self.server_status_event(
                event_fire=self.web_socket.retry_backoff == 1,
                # node=self.web_socket.api_node,
                unavailable=self.web_socket.api_node,
            )
            self.web_socket.retry_backoff += 1
            _LOGGER.warning("WebSocket error: %s, falling back to HTTP", str(ex))
            return False

        self.update_interval = self.config_entry.runtime_data.update_interval
        return True

    async def _handle(self, resp: dict[str, Any]) -> None:
        """Handle incoming WebSocket messages based on type."""
        event_type = resp.get("type")

        # Handled message on type
        match event_type:
            case "eew":
                data: dict[str, Any] = resp.get("data", {})
                flag = await self.data_client.load_recent_data(data)

                # Event bus fired
                if flag:
                    self.hass.bus.fire(
                        f"{DOMAIN}_notification",
                        {"earthquake": data},
                        origin=EventOrigin.remote,
                    )

            case "report":
                data: dict[str, Any] = resp.get("data", {})
                flag = await self.data_client.load_report_data(data)

                # Event bus fired
                if flag:
                    self.hass.bus.fire(
                        f"{DOMAIN}_report",
                        {"earthquake": data},
                        origin=EventOrigin.remote,
                    )

            case "intensity":
                coordinator_data = self.data
                resp.pop("type", None)
                coordinator_data["recent"]["intensity"] = resp
                _LOGGER.debug("Intensity data: %s", resp)
                self.async_set_updated_data(coordinator_data)

            case "tsunami":
                coordinator_data = self.data
                tsunami_data: dict = resp.get("data", {})
                tsunami_data.setdefault("time", resp.get("time", 0))
                coordinator_data["recent"]["tsunami"] = tsunami_data
                _LOGGER.debug("Tsunami Data: %s", tsunami_data)
                self.async_set_updated_data(coordinator_data)

    async def server_status_event(self, **kwargs):
        """Server status update trigger event."""
        server_status = await self.data_client.server_status(**kwargs)
        protocol, _ = await self.data_client.api_node()

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

    def websocket_is_online(self):
        if self.web_socket is None:
            return False

        ws_state = self.web_socket.state
        return ws_state.is_running and ws_state.subscrib_service

    def retry_backoff(self, retry):
        new_interval = min(
            BASE_INTERVAL * retry,
            MAX_INTERVAL,
        )
        self.update_interval = new_interval
        _LOGGER.error(
            "Update failed, next attempt in %s seconds",
            new_interval.total_seconds(),
        )
        raise UpdateFailed

    @property
    def http_client(self):
        return self.config_entry.runtime_data.http_client

    @property
    def web_socket(self):
        return self.config_entry.runtime_data.web_socket
