"""WebSocket for TREM2 component."""

from __future__ import annotations

import asyncio
from asyncio import Task
from dataclasses import dataclass
from enum import Enum
import json
from logging import Logger
import random
from time import monotonic
from typing import Any

from aiohttp import (
    ClientConnectionResetError,
    ClientSession,
    ClientWebSocketResponse,
    WSMsgType,
    WSServerHandshakeError,
)
from aiohttp.hdrs import USER_AGENT

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import HA_USER_AGENT, WS_URLS


class WebSocketService(Enum):
    """Represent the supported WebSocket service."""

    REALTIME_STATION = "trem.rts"  # 即時地動資料
    REALTIME_WAVE = "trem.rtw"  # 即時地動波形圖資料
    EEW = "websocket.eew"  # 地震速報資料
    TREM_EEW = "trem.eew"  # TREM 地震速報資料
    REPORT = "websocket.report"  # 中央氣象署地震報告資料
    TSUNAMI = "websocket.tsunami"  # 中央氣象署海嘯資訊資料
    CWA_INTENSITY = "cwa.intensity"  # 中央氣象署震度速報資料
    TREM_INTENSITY = "trem.intensity"  # TREM 震度速報資料


@dataclass
class ExpTechWSConf:
    """WebSocket configuration for TREM2 component."""

    # Configuration
    access_token = "c0d30WNER$JTGAO"
    register_service = [
        WebSocketService.CWA_INTENSITY,
        WebSocketService.EEW,
        WebSocketService.REPORT,
        WebSocketService.TREM_INTENSITY,
        WebSocketService.TSUNAMI,
    ]
    params = {}


@dataclass
class ExpTechWSState:
    """WebSocket State and Task for TREM2 component."""

    # State
    conn: ClientWebSocketResponse | None = None
    credentials: dict | None = None
    subscrib_service: list | None = None
    is_running = False
    message: dict | None = None

    # Connection
    ping_time: float = 0
    pong_time: float = 0

    # Task
    hass: HomeAssistant | None = None
    heartbeat_task: Task | None = None
    listen_task: Task | None = None


class ExpTechWSClient:
    """Manage WebSocket connections and message reception."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        logger: Logger,
        *,
        api_node=None,
        base_url=None,
        unavailables: list[str] | None = None,
    ) -> None:
        """Initialize the WebSocket client."""
        self.unavailables: list[str] = unavailables or []
        self.logger = logger
        self.api_node: str | None
        self.base_url: str | None
        self.api_node, self.base_url = self.initialize_route(
            api_node=api_node,
            base_url=base_url,
            unavailables=self.unavailables,
        )
        self.session: ClientSession = session
        self.conf = ExpTechWSConf()
        self.state = ExpTechWSState()
        self.state.hass = hass

    async def reconnect(self, close_code=999):
        """Reconnect to the WebSocket server."""
        if self.state.conn and not self.state.conn.closed:
            await self.state.conn.close(
                code=close_code,
                message=b"reconnect",
            )

        self.state.credentials = None
        self.state.is_running = False

        await self.connect()

    async def disconnect(self, close_code=999):
        """Close the active WebSocket connection and reset credentials."""
        if self.state.listen_task:
            self.state.listen_task.cancel()
            self.state.listen_task = None

        if self.state.heartbeat_task:
            self.state.heartbeat_task.cancel()
            self.state.heartbeat_task = None

        if self.state.conn and not self.state.conn.closed:
            await self.state.conn.close(
                code=close_code,
                message=b"disconnect",
            )

        self.state.conn = None
        self.state.credentials = None
        self.state.is_running = False

    async def connect(self, params: dict | None = None):
        """Establish a new WebSocket connection.

        Args:
            params (dict, optional): Query parameters to append to the URL.

        Returns:
            ClientWebSocketResponse: The connected WebSocket object, or None if session is not set.

        """
        if self.session is None:
            return None

        if self.state.is_running:
            await self.disconnect()

        if self.base_url is None:
            raise RuntimeError("WS Client base URL is not set")

        # Establishing a connection
        try:
            self.conf.params = params or {}
            headers = {
                USER_AGENT: HA_USER_AGENT,
            }
            self.state.conn = await self.session.ws_connect(
                self.base_url,
                headers=headers,
                autoclose=False,
                autoping=False,
            )
        except WSServerHandshakeError as err:
            hass = self.state.hass
            # entry_id = hass.config_entry.entry_id
            # hass.async_create_task(hass.config_entries.async_reload(entry_id))
            raise HomeAssistantError from err

        # Initialize background tasks and verify
        self.initialize_background_tasks()
        await self._verify()

        return self.state.conn

    async def _listen(self):
        """Listen for incoming WebSocket messages and process events.

        Continuously receives messages from the active WebSocket connection.
        If the connection is lost, attempts to reconnect.
        """
        self.state.is_running = True
        retries = 0
        max_retries = 5

        while self.state.conn:
            if self.state.conn.closed:
                if self.state.conn.close_code == 999:
                    self.logger.debug("(listener) WebSocket connection closed, disconnecting...")
                    break

                await asyncio.sleep(3)
                continue

            # Extract the message type and data from the WSMessage object.
            self.state.is_running = True
            try:
                raw_message = await self.state.conn.receive()
                raw_type = raw_message.type
                raw_data = raw_message.data
                raw_extra = raw_message.extra

                # Process the message type and data using the custom handler.
                self.state.message = await self._handle(raw_type, raw_data, raw_extra)
                retries = 0
            except (RuntimeError, ConnectionResetError):
                retries += 1
                await asyncio.sleep(3)
                if retries >= max_retries:
                    self.logger.error("Max retries reached, WebSocket connection failures")
                    break

        self.state.is_running = False

    async def _handle(self, raw_type: WSMsgType, raw_data, extra) -> dict | None:
        """Handle incoming WebSocket messages based on type and event."""
        if self.state.conn:
            match raw_type:
                case WSMsgType.CLOSE | WSMsgType.CLOSED | WSMsgType.CLOSING | WSMsgType.ERROR:
                    if self.state.conn.close_code == 999:
                        return None

                    self.logger.debug(
                        "(handle) WebSocket failing connection with code %s",
                        self.state.conn.close_code,
                    )
                    await self.reconnect()

                    return self.state.message
                case WSMsgType.PONG:
                    self.state.pong_time = monotonic()
                    self.logger.debug("(handle) < %s %s", raw_type.name, raw_data)

                    return self.state.message
                case WSMsgType.PING:
                    self.state.ping_time = monotonic()
                    self.logger.debug("(handle) < %s %s", raw_type.name, raw_data)

                    await self.state.conn.pong(raw_data)

                    self.state.pong_time = monotonic()
                    self.logger.debug("(handle) > %s %s", "PONG", raw_data)

                    return self.state.message
                case WSMsgType.TEXT:
                    payload = json.loads(raw_data)
                    return await self._parse_text(payload)
                case _:
                    self.logger.warning("Unhandled message type: %s", raw_type.name)

        return None

    async def _parse_text(self, payload: dict) -> dict | None:
        event = payload.get("type")
        msg_data: dict = payload.get("data", {})

        match event:
            case "verify":
                await self._verify()

                return msg_data
            case "info":
                msg_code = msg_data.get("code")
                if msg_code == 200:
                    self.state.subscrib_service = msg_data.get("list", [])
                if msg_code == 401:
                    self.state.credentials = None
                if msg_code == 503:
                    await asyncio.sleep(5)

                return msg_data
            case "data" | "ntp":
                return msg_data
            case _:
                self.logger.warning("Unhandled event: %s", event)

        return None

    async def _keepalive(self):
        """Perform WebSocket pingpong."""
        while self.state.conn and self.state.is_running:
            if self.state.conn.closed:
                if self.state.conn.close_code == 999:
                    self.logger.debug("(heartbeat) WebSocket is disconnecting")
                    break

                await asyncio.sleep(3)
                continue

            try:
                self.state.ping_time = monotonic()
                self.logger.debug("(heartbeat) > PING")
                await self.state.conn.ping()
                await asyncio.sleep(30)
            except ClientConnectionResetError:
                await asyncio.sleep(3)
                continue

    async def recv(self) -> dict[str, Any] | None:
        """Fetch data from the ExpTech server via WebSocket.

        Returns:
            list | None: The received message(s) or None if not available.

        """
        if not self.state.conn:
            raise ConnectionError("WebSocket connection is not established")

        return self.state.message

    def initialize_route(self, action="class", **kwargs) -> tuple:
        """Randomly select a node for HTTP connection.

        Args:
            action: Required keyword arguments:
                - class: Assign arguments by returning results via tuple
                - service: When calling through the service, the original arguments will be replaced.
            **kwargs: Arbitrary keyword arguments. Can include:
                - api_node (str, optional): Specific api_node to use.
                - base_url (str, optional): Specific base URL to use.
                - unavailables (list, optional): List of nodes to exclude.

        Returns:
            tuple: The API Node information.

        """
        base_url: str = kwargs.get("base_url", "")
        api_node: str = kwargs.get("api_node") or base_url

        match (base_url, api_node):
            case (url, _) if url:
                self.unavailables = []
            case (_, node) if node in WS_URLS:
                self.unavailables = []
                base_url = WS_URLS[node]
            case _:
                api_nodes = [k for k in WS_URLS if k not in self.unavailables]
                if not api_nodes:
                    raise RuntimeError("No available nodes")
                api_node = random.choice(api_nodes)
                base_url = WS_URLS[api_node]

        if action == "service":
            self.api_node = api_node
            self.base_url = base_url

        return (api_node, base_url)

    async def _verify(self):
        if self.state.conn and self.state.credentials is None:
            self.state.credentials = {
                "type": "start",
                "key": self.conf.access_token,
                "service": [k.value for k in self.conf.register_service],
            }

            await self.state.conn.send_json(self.state.credentials)

    def initialize_background_tasks(self):
        """Initialize and manage background tasks for WebSocket operations."""

        def handle_task_exception(task: Task):
            """Handle exceptions or cancellations from a background task."""
            if task.cancelled():
                self.logger.debug("Task: %s was cancelled", task.get_name())
                return

            try:
                exc = task.exception()
            except asyncio.CancelledError:
                self.logger.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
                return
            except Exception as ex:
                self.logger.error("Error retrieving task exception: %s", ex)
                return

            if exc:
                self.logger.error("Task failed: %s", repr(exc))

        # Create and manage the listener task
        if self.state.hass:
            if self.state.listen_task and not self.state.listen_task.done():
                self.logger.debug("Task: %s is already running", self.state.listen_task.get_name())
            else:
                self.state.listen_task = self.state.hass.async_create_background_task(
                    self._listen(),
                    name="websocket client listener",
                )
                self.state.listen_task.add_done_callback(handle_task_exception)

            # Create and manage the keepalive task
            if self.state.heartbeat_task and not self.state.heartbeat_task.done():
                self.logger.debug("Task: %s is already running", self.state.heartbeat_task.get_name())
            else:
                self.state.heartbeat_task = self.state.hass.async_create_background_task(
                    self._keepalive(),
                    name="websocket client heartbeat",
                )
                self.state.heartbeat_task.add_done_callback(handle_task_exception)
