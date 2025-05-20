"""HTTP Client for TREM2 component."""

from __future__ import annotations

import random
import re
from time import monotonic

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.hdrs import ACCEPT, CONTENT_TYPE, METH_GET, USER_AGENT
from homeassistant.const import CONTENT_TYPE_JSON
from logging import Logger

from ..const import (
    API_VERSION,
    BASE_URLS,
    HA_USER_AGENT,
    REPORT_URL,
    REQUEST_TIMEOUT,
)


class ExpTechHTTPClient:
    """Manage HTTP connections and message reception."""

    def __init__(
        self,
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
        self.params = {}
        self.latency: float = 0

    async def fetch_eew(self) -> list | None:
        """Fetch earthquake data from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.

        """
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
                url=self.base_url,
                params=self.params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError, RuntimeError) as ex:
            self.logger.error(
                "Failed fetching data from HTTP API(%s), %s",
                self.api_node,
                str(ex),
            )
        else:
            if response.ok:
                if len(self.unavailables) > 0:
                    self.unavailables = []

                resp = await response.json()
                self.latency = abs(monotonic() - start)
                return resp

            self.logger.error(
                "Failed fetching data from HTTP API(%s), (HTTP Status Code = %s)",
                self.api_node,
                response.status,
            )

        raise RuntimeError("An error occurred during message reception")

    async def fetch_report(self, local_report: dict | None = None) -> dict | None:
        """Fetch report summary from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.

        """
        if local_report is None:
            local_report = {}

        try:
            headers = {
                ACCEPT: CONTENT_TYPE_JSON,
                CONTENT_TYPE: CONTENT_TYPE_JSON,
                USER_AGENT: HA_USER_AGENT,
            }

            response = await self.session.request(
                method=METH_GET,
                url=REPORT_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (ClientConnectorError, TimeoutError) as ex:
            self.logger.error("Failed fetching data from report server, %s", str(ex))
        else:
            if response.ok:
                resp = await response.json()
                if resp:
                    pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
                    filtered = [d for d in resp if re.search(pattern, d.get("id", ""))]
                    fetch_report: dict = filtered[0] if filtered else resp[0]
                    fetch_report.setdefault("author", "cwa" if filtered else "ExpTech")
                    fetch_report_id = fetch_report.get("id", "")
                    local_report_id = local_report.get("id", "")

                    # Check if the report data is up to date
                    if fetch_report_id in {"", local_report_id}:
                        return fetch_report

                    report_data = await self.fetch_report_detail(fetch_report_id) or fetch_report
                    report_data.setdefault("author", fetch_report.get("author", "ExpTech"))
                    return report_data

                self.logger.debug("Report data is empty")

            self.logger.error(
                "Failed fetching data from report server, (HTTP Status Code = %s)",
                response.status,
            )

        return None

    async def fetch_report_detail(self, report_id) -> dict | None:
        """Fetch report detail from the ExpTech server via HTTP.

        Returns:
            list | None: The received message(s) or None if not available.

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
            self.logger.error("Failed fetching data from report server, %s", str(ex))
        else:
            if response.ok:
                return await response.json()

        self.logger.error(
            "Failed fetching data from report server, (HTTP Status Code = %s)",
            response.status,
        )

        return None

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
            case (_, node) if node in BASE_URLS:
                self.unavailables = []
                base_url = f"{BASE_URLS[node]}/api/v{API_VERSION}/eq/eew"
            case _:
                api_nodes = [k for k in BASE_URLS if k not in self.unavailables]
                if not api_nodes:
                    raise RuntimeError("No available nodes")
                api_node = random.choice(api_nodes)
                base_url = f"{BASE_URLS[api_node]}/api/v{API_VERSION}/eq/eew"

        if action == "service":
            self.api_node = api_node
            self.base_url = base_url

        return (api_node, base_url)
