"""Runtime Data Class for TREM2 component."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from .api.http import ExpTechHTTPClient
    from .api.websocket import ExpTechWSClient
    from .update_coordinator import Trem2UpdateCoordinator


class ExpTechClient:
    """Class to help client threads."""

    def __init__(self, http: ExpTechHTTPClient, websocket: ExpTechWSClient) -> None:
        """Initialize the client."""
        self.http = http
        self.websocket = websocket
        self.retry_backoff = 1
        self.use_http_fallback = False
        self.fetch_report = False
        self.update_interval = timedelta(seconds=5)

    async def api_node(self):
        """Return current connection mode."""
        if self.use_http_fallback:
            return ("http (fallback)", self.http.api_node)
        else:
            if self.websocket.state.is_running:
                return ("websocket", self.websocket.api_node)

        return ("http", self.http.api_node)

    async def server_status(self, **kwargs):
        """Return current server status."""
        if "update_interval" in kwargs:
            self.update_interval = kwargs["update_interval"]

        _, api_node = await self.api_node()

        return {
            "current_node": kwargs.get("node", api_node),
            "unavailable": kwargs.get("unavailable", []),
            "latency": await self._connection_latency(),
        }

    async def _connection_latency(self) -> float | str:
        """Return current latency."""
        update_interval = self.update_interval.total_seconds()
        protocol, _ = await self.api_node()

        if protocol == "websocket" and not self.use_http_fallback:
            latency = abs(
                self.websocket.state.ping_time - self.websocket.state.pong_time,
            )
        else:
            latency = self.http.latency + (update_interval if update_interval > 1 else 0)

        return f"{latency:.3f}" if latency < 6 else "6s+"


@dataclass
class ExpTechConf:
    """Class to help TREM2 config."""

    fast_interval = timedelta(seconds=1)
    base_interval = timedelta(seconds=5)
    retrie_interval = timedelta(minutes=5)
    max_interval = timedelta(minutes=15)
    params = {}


@dataclass
class Trem2RuntimeData:
    """Class to help runtime data."""

    name: str
    coordinator: Trem2UpdateCoordinator
    recent_sotre: Store
    report_store: Store
    platforms: list[Platform]
    selected_option: str | None = None


@dataclass
class Trem2ImageData:
    """Class to help image data."""

    image_id: str | None = None
    image: bytes | None = None
    attributes = {}
    attr_value = {}
    intensitys = {}
