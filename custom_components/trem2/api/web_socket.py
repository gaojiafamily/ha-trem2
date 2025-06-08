"""WebSocket for TREM2 component."""

from __future__ import annotations

from asyncio import CancelledError, Task, sleep
import json
import logging
from time import monotonic
from typing import TYPE_CHECKING, Any

from aiohttp import ClientConnectionResetError, ClientSession, WSMsgType, WSServerHandshakeError
from aiohttp.hdrs import USER_AGENT

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import HA_USER_AGENT, WS_URLS
from ..models import DictKeyExclusionCycler, EndPoint, ExpTechClient

if TYPE_CHECKING:
    from runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


class ExpTechWSClient(ExpTechClient):
    """Manage WebSocket connections and message reception."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        hass: HomeAssistant,
        session: ClientSession,
        access_token: str,
    ) -> None:
        """Initialize the WebSocket client."""
        super().__init__(
            session=session,
            node_cycler=DictKeyExclusionCycler(WS_URLS),
        )

        self.config_entry = config_entry
        self.hass = hass
        self.api_node = None
        self.base_url = None
        self.unavailables = None

        self.access_token: str = access_token
        self.heartbeat_task: Task | None = None
        self.listen_task: Task | None = None

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
        if self.listen_task:
            self.listen_task.cancel()
            self.listen_task = None

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

        if self.state.conn and not self.state.conn.closed:
            await self.state.conn.close(
                code=close_code,
                message=b"disconnect",
            )

        self.state.conn = None
        self.state.credentials = None
        self.state.is_running = False

    async def connect(self):
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
            headers = {
                USER_AGENT: HA_USER_AGENT,
            }
            self.state.conn = await self.session.ws_connect(
                str(self.base_url),
                headers=headers,
                autoclose=False,
                autoping=False,
            )
        except WSServerHandshakeError as err:
            entry_id = self.config_entry.entry_id
            self.hass.async_create_task(self.hass.config_entries.async_reload(entry_id))
            raise HomeAssistantError("The ExpTech server is not responding") from err

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
                    _LOGGER.debug("(listener) WebSocket connection closed, disconnecting")
                    break

                await sleep(3)
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
                await sleep(3)
                if retries >= max_retries:
                    _LOGGER.error("Max retries reached, WebSocket connection failures")
                    break

        self.state.is_running = False

    async def _handle(self, raw_type: WSMsgType, raw_data, extra) -> dict | None:
        """Handle incoming WebSocket messages based on type and event."""
        if self.state.conn:
            match raw_type:
                case WSMsgType.CLOSE | WSMsgType.CLOSED | WSMsgType.CLOSING | WSMsgType.ERROR:
                    if self.state.conn.close_code == 999:
                        return None

                    _LOGGER.debug(
                        "(handle) WebSocket failing connection with code %s",
                        self.state.conn.close_code,
                    )
                    await self.reconnect()

                    return self.state.message
                case WSMsgType.PONG:
                    self.state.pong_time = monotonic()
                    _LOGGER.debug("(handle) < %s %s", raw_type.name, raw_data)

                    return self.state.message
                case WSMsgType.PING:
                    self.state.ping_time = monotonic()
                    _LOGGER.debug("(handle) < %s %s", raw_type.name, raw_data)

                    await self.state.conn.pong(raw_data)

                    self.state.pong_time = monotonic()
                    _LOGGER.debug("(handle) > %s %s", "PONG", raw_data)

                    return self.state.message
                case WSMsgType.TEXT:
                    payload = json.loads(raw_data)
                    return await self._parse_text(payload)
                case _:
                    _LOGGER.warning("Unhandled message type: %s", raw_type.name)

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
                    await sleep(5)

                return msg_data
            case "data" | "ntp":
                return msg_data
            case _:
                _LOGGER.warning("Unhandled event: %s", event)

        return None

    async def _keepalive(self):
        """Perform WebSocket pingpong."""
        while self.state.conn and self.state.is_running:
            if self.state.conn.closed:
                if self.state.conn.close_code == 999:
                    _LOGGER.debug("(heartbeat) WebSocket is disconnecting")
                    break

                await sleep(3)
                continue

            try:
                self.state.ping_time = monotonic()
                _LOGGER.debug("(heartbeat) > PING")
                await self.state.conn.ping()
                await sleep(30)
            except ClientConnectionResetError:
                await sleep(3)
                continue

    async def _verify(self):
        if self.state.conn and self.state.credentials is None:
            self.state.credentials = {
                "type": "start",
                "key": self.access_token,
                "service": [k.value for k in self.register_service],
            }

            await self.state.conn.send_json(self.state.credentials)

    async def recv(self) -> dict[str, Any]:
        """Fetch data from the ExpTech server via WebSocket.

        Returns:
            list: The received message(s).

        """
        if not self.state.conn:
            raise ConnectionError("WebSocket connection is not established")

        if self.state.message is None:
            raise RuntimeError("An error occurred during message handling")

        return self.state.message

    async def initialize_route(
        self,
        *,
        api_node: str | None = None,
        base_url: EndPoint | str | None = None,
        unavailables: list[str] | None = None,
    ):
        """Randomly select a node for WebSocket connection.

        Args:
            api_node (str, optional): Specific api_node to use.
            base_url (str, optional): Specific base URL to use.
            unavailables (list, optional): List of nodes to exclude.

        """
        if unavailables is None:
            unavailables = []

        self.unavailables = unavailables
        match (base_url, api_node):
            case (url, _) if url:
                self.api_node = str(url)
                self.base_url = EndPoint.model_validate(url)
                self.unavailables.clear()
            case (_, node) if node in WS_URLS:
                self.api_node = node
                self.base_url = EndPoint.model_validate(WS_URLS[node])
                self.unavailables.clear()
            case _:
                self.node_cycler.update_exclusions(self.unavailables)
                node, url = self.node_cycler.next()
                if node is None:
                    raise RuntimeError("No available nodes")

                self.api_node = node
                self.base_url = EndPoint.model_validate(url)

    def initialize_background_tasks(self):
        """Initialize and manage background tasks for WebSocket operations."""

        def handle_task_exception(task: Task):
            """Handle exceptions or cancellations from a background task."""
            if task.cancelled():
                _LOGGER.debug("Task: %s was cancelled", task.get_name())
                return

            try:
                exc = task.exception()
            except CancelledError:
                _LOGGER.debug("Task exception retrieval was cancelled (Home Assistant is stopping)")
                return
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error("Error retrieving task exception: %s", ex)
                return

            if exc:
                _LOGGER.error("Task failed: %s", repr(exc))

        # Create and manage the listener task
        if self.hass:
            if self.listen_task and not self.listen_task.done():
                _LOGGER.debug("Task: %s is already running", self.listen_task.get_name())
            else:
                self.listen_task = self.hass.async_create_background_task(
                    self._listen(),
                    name="websocket client listener",
                )
                self.listen_task.add_done_callback(handle_task_exception)

            # Create and manage the keepalive task
            if self.heartbeat_task and not self.heartbeat_task.done():
                _LOGGER.debug("Task: %s is already running", self.heartbeat_task.get_name())
            else:
                self.heartbeat_task = self.hass.async_create_background_task(
                    self._keepalive(),
                    name="websocket client heartbeat",
                )
                self.heartbeat_task.add_done_callback(handle_task_exception)
