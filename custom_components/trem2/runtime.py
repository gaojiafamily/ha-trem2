"""Runtime Data Class for TREM2 component."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from aiohttp import ClientWebSocketResponse

from homeassistant.const import Platform

if TYPE_CHECKING:
    from .api.http_client import ExpTechHTTPClient
    from .api.web_socket import ExpTechWSClient
    from .store import StoreHandler
    from .update_coordinator import Trem2UpdateCoordinator


@dataclass(kw_only=True, slots=True)
class Trem2RuntimeData:
    """A container for runtime data and objects shared across platforms for a single config entry."""

    coordinator: Trem2UpdateCoordinator
    sotre_handler: StoreHandler
    platforms: list[Platform]
    update_interval: timedelta

    http_client: ExpTechHTTPClient
    web_socket: ExpTechWSClient | None = None
    params: dict[str, Any] = field(default_factory=dict[str, Any])
    fetch_report = False

    selected_option: str | None = None


@dataclass
class Trem2ImageData:
    """Class to help image data."""

    image_id: str | None = None
    image: bytes | None = None
    attributes = {}
    attr_value = {}
    intensitys = {}


@dataclass
class WebSocketState:
    """WebSocket State and Task for runtime data."""

    # State
    conn: ClientWebSocketResponse | None = None
    credentials: dict | None = None
    subscrib_service: list | None = None
    is_running = False
    message: dict | None = None

    # Connection
    ping_time: float = 0
    pong_time: float = 0
