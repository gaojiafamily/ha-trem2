"""WebSocket for TREM2 component."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from aiohttp.hdrs import USER_AGENT
from logging import Logger
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_API_TOKEN
import random
import asyncio
from asyncio import Task
import json


from ..const import (
    API_VERSION,
    WS_URLS,
    HA_USER_AGENT,
)
from ..exceptions import NoAvailableNodesError


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
        WebSocketService.EEW,
        WebSocketService.TSUNAMI,
        WebSocketService.REPORT,
        WebSocketService.REALTIME_STATION,
        WebSocketService.CWA_INTENSITY,
        WebSocketService.TREM_EEW,
    ]
    params = {}


@dataclass
class ExpTechWSState:
    """WebSocket State and Task for TREM2 component."""

    # State
    conn: ClientWebSocketResponse = None
    credentials: dict | None = None
    subscrib_service = None
    is_running = False
    message = ""

    # Connection
    ping_time: float = 0
    pong_time: float = 0
    latency: float = 0

    # Task
    hass: HomeAssistant = None
    keepalive_task: Task = None
    lock = asyncio.Lock()
    receive_task: Task = None


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
        unavailables=None,
    ) -> None:
        """Initialize the WebSocket client."""
        self.unavailables = unavailables or []
        self.logger = logger
        self.api_node, self.base_url = self.initialize_route(
            api_node=api_node,
            base_url=base_url,
            unavailables=self.unavailables,
        )
        self.session = session
        self.conf = ExpTechWSConf()
        self.state = ExpTechWSState()
        self.state.hass = hass

    async def reconnect(self):
        """Reconnect the WebSocket connection.

        Closes the existing connection if present, then establishes a new connection.
        """
        async with self.state.lock:
            await self.disconnect()
            await self.connect()

    async def disconnect(self):
        """Close the active WebSocket connection and reset credentials."""
        if self.state.conn:
            await self.state.conn.close()
            self.state.conn = None

        if self.state.receive_task:
            self.state.receive_task.cancel()
            self.state.receive_task = None

        if self.state.keepalive_task:
            self.state.keepalive_task.cancel()
            self.state.keepalive_task = None

        self.state.credentials = None
        self.state.is_running = False

    async def connect(self, params=None):
        """Establish a new WebSocket connection.

        Args:
            params (dict, optional): Query parameters to append to the URL.

        Returns:
            ClientWebSocketResponse: The connected WebSocket object, or None if session is not set.
        """
        if self.session is None:
            return None

        # WSManager is initializing
        if self.state.is_running:
            await self.disconnect()
        self.conf.params = params

        # Establishing a connection
        headers = {
            USER_AGENT: HA_USER_AGENT,
        }
        self.state.conn = await self.session.ws_connect(
            self.base_url,
            headers=headers,
            autoping=False,
        )

        # Initialize background tasks and verify
        self.initialize_background_tasks()
        await self._verify()

        return self.state.conn

    async def listen(self):
        """Listen for incoming WebSocket messages and process events.

        Continuously receives messages from the active WebSocket connection.
        If the connection is lost, attempts to reconnect.
        """
        self.state.is_running = True
        retries = 0
        max_retries = 5

        while self.state.is_running:
            await asyncio.sleep(1)
            if self.state.conn is None or self.state.conn.closed:
                continue

            # Extract the message type and data from the WSMessage object.
            try:
                raw_message = await self.state.conn.receive()
                raw_type = raw_message.type
                raw_data = raw_message.data

                # Process the message type and data using the custom handler.
                self.state.message = await self._handle(raw_type, raw_data)
                retries = 0
            except (RuntimeError, ConnectionResetError):
                retries += 1
                if retries >= max_retries:
                    self.logger.error("Max retries reached, WebSocket connection failures")
                    break
                await asyncio.sleep(2**retries)

    async def _handle(self, type, data):
        """Handle incoming WebSocket messages based on type and event."""
        if type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING}:
            return None

        payload: dict = json.loads(data)
        event = payload.get("type")
        msg_data: dict = payload.get("data", {})

        if type is WSMsgType.PONG:
            self.state.pong_time = time()
            self.state.latency = abs(time() - self.state.ping_time)
            return msg_data

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
                self.logger.debug("Unhandled event: %s", event)
                return None

    async def _keepalive(self):
        """Perform WebSocket pingpong."""
        while self.state.is_running:
            await asyncio.sleep(30)
            if self.state.conn and not self.state.conn.closed:
                self.state.ping_time = time()
                await self.state.conn.ping()

    async def recv(self):
        """Fetch data from the ExpTech server via WebSocket.

        Returns:
            list | None: The received message(s) or None if not available.
        """
        if not self.state.conn:
            raise ConnectionResetError

        if self.state.message is None:
            raise RuntimeError

        return self.state.message

    def initialize_route(self, action="class", **kwargs) -> tuple | bool:
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
        base_url = kwargs.get("base_url")
        api_node = kwargs.get("api_node", base_url)

        match (base_url, api_node):
            case (url, _) if url:
                self.unavailables = []
            case (_, node) if node in WS_URLS:
                self.unavailables = []
                base_url = WS_URLS[node]
            case _:
                api_nodes = [k for k in WS_URLS if k not in self.unavailables]
                if not api_nodes:
                    raise NoAvailableNodesError
                api_node = random.choice(api_nodes)
                base_url = WS_URLS[api_node]

        if action == "service":
            self.api_node = api_node
            self.base_url = base_url

        return (api_node, base_url)

    async def _verify(self):
        if self.state.credentials is None:
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
                self.logger.debug("Background task was cancelled")
                return

            try:
                exc = task.exception()
            except asyncio.CancelledError:
                self.logger.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
                return
            except Exception as ex:
                self.logger.error("Error retrieving task exception: %s", ex, exc_info=True)
                return

            if exc:
                self.logger.error("ExpTech WS lister task failed: %s", exc, exc_info=exc)

        # Create and manage the listener task
        self.state.receive_task = self.state.hass.async_create_background_task(
            self.listen(),
            name="ws_client_listener",
        )
        self.state.receive_task.add_done_callback(handle_task_exception)

        # Create and manage the keepalive task
        self.state.keepalive_task = self.state.hass.async_create_background_task(
            self._keepalive(),
            name="ws_client_heartbeat",
        )
        self.state.keepalive_task.add_done_callback(handle_task_exception)

        # 守護進程
