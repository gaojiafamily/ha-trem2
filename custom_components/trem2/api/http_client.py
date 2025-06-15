"""HTTP Client for TREM2 component."""

from __future__ import annotations

import logging
from time import monotonic
from typing import TYPE_CHECKING, Any

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import HomeAssistant

from ..const import API_VERSION, BASE_URLS, HA_USER_AGENT, REPORT_URL, REQUEST_TIMEOUT
from ..models import DictKeyExclusionCycler, EndPoint, ExpTechClient

if TYPE_CHECKING:
    from runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


class ExpTechHTTPClient(ExpTechClient):
    """Manage HTTP connections and message reception."""

    def __init__(
        self,
        config_entry: Trem2ConfigEntry,
        hass: HomeAssistant,
        session: ClientSession,
        *,
        api_node=None,
        base_url: EndPoint | None = None,
        unavailables: list[str] | None = None,
    ) -> None:
        """Initialize the HTTP client."""
        super().__init__(
            session=session,
            node_cycler=DictKeyExclusionCycler(BASE_URLS),
        )

        self.config_entry = config_entry
        self.hass = hass
        self.api_node = None
        self.base_url = None
        self.unavailables = None

        self.latency: float = 0

    async def fetch_eew(self) -> list[dict[str, Any]] | None:
        """Fetch earthquake data from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.

        """
        resp = None
        start = monotonic()

        if self.base_url is None:
            raise RuntimeError("HTTP Client base URL is not set")

        # Fetch eew data
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await self.session.request(
                method=METH_GET,
                url=str(self.base_url),
                params=self.config_entry.runtime_data.params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError, RuntimeError) as ex:
            _LOGGER.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.api_node,
                str(ex),
            )
        else:
            if response.ok:
                if self.unavailables and len(self.unavailables) > 0:
                    self.unavailables.clear()

                resp = await response.json()
                self.latency = abs(monotonic() - start)
            else:
                _LOGGER.error(
                    "Failed fetching data from HTTP API(%s), (HTTP Status Code = %s)",
                    self.api_node,
                    response.status,
                )

            if resp is not None:
                return resp

        raise RuntimeError("An error occurred during message reception")

    async def fetch_report(self, limit=5) -> list[dict[str, Any]]:
        """Fetch report summary from the ExpTech server via HTTP.

        Returns:
            list: The received message(s) or empty list.

        """
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }
            params = {"limit": limit}

            response = await self.session.request(
                method=METH_GET,
                url=REPORT_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            _LOGGER.error("Failed fetching data from report server, %s", str(ex))
        else:
            if response.ok:
                return await response.json()

            _LOGGER.error(
                "Failed fetching data from report server, (HTTP Status Code = %s)",
                response.status,
            )

        return []

    async def fetch_report_detail(self, report_id) -> dict[str, Any]:
        """Fetch report detail from the ExpTech server via HTTP.

        Returns:
            dict: The report data detail.

        """
        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await self.session.request(
                method=METH_GET,
                url=f"{REPORT_URL}/{report_id}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            _LOGGER.error("Failed fetching data from report server, %s", str(ex))
        else:
            if response.ok:
                return await response.json()

        _LOGGER.error(
            "Failed fetching data from report server, (HTTP Status Code = %s)",
            response.status,
        )

        return {}

    async def initialize_route(
        self,
        *,
        api_node: str | None = None,
        base_url: EndPoint | str | None = None,
        unavailables: list[str] | None = None,
    ):
        """Randomly select a node for HTTP connection.

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
            case (_, node) if node in BASE_URLS:
                self.api_node = node
                self.base_url = EndPoint.model_validate(
                    f"{BASE_URLS[node]}/api/v{API_VERSION}/eq/eew",
                )
                self.unavailables.clear()
            case _:
                self.node_cycler.update_exclusions(self.unavailables)
                node, url = self.node_cycler.next()
                if node is None:
                    raise RuntimeError("No available nodes")

                self.api_node = node
                self.base_url = EndPoint.model_validate(
                    f"{url}/api/v{API_VERSION}/eq/eew",
                )
