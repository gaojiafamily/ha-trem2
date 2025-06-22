"""Processing Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ATTR_COUNTY, COUNTY_TOWN, ZIP3_TOWN
from .core.earthquake import intensity_to_text

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

_LOGGER = logging.getLogger(__name__)

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


class Trem2DataClient:
    """Defines stored for TREM2."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: Trem2ConfigEntry,
    ) -> None:
        """Initialize the stored."""
        self.hass = hass
        self.config_entry = config_entry

    async def load_recent_data(self, data: dict[str, Any] | None = None) -> bool:
        """Perform recent data processing."""
        default_data = {
            "cache": [],
            "earthquake": {},
            "intensity": {},
            "tsunami": {},
            "simulating": {},
        }
        coordinator_data = self.coordinator.data

        # Load recent data from stored
        store_eew = self.sotre_handler.get_store("recent")
        store_data = await store_eew.async_load()
        coordinator_data.setdefault("recent", store_data or default_data)

        # Check earthquake data if not None
        if data:
            try:
                cache: list[dict[str, Any]] = coordinator_data["recent"]["cache"]
                seen = {(d["id"], d.get("serial", "")) for d in cache}
                key = (data["id"], data.get("serial", ""))
                if key in seen:
                    return False
            except KeyError as e:
                _LOGGER.error(e)

            # Stored earthquake data to runtime data
            data.pop("type", None)
            data.setdefault("time", data.get("time", 0))
            provider = self.config_entry.runtime_data.params.get("type")
            if provider == "" or data.get("author") == provider:
                coordinator_data["recent"]["earthquake"] = data

            # Stored to earthquake cache
            new_cache = cache.copy()
            new_cache.insert(0, data)
            coordinator_data["recent"]["cache"] = new_cache[:10]
            await store_eew.async_save(
                coordinator_data["recent"],
            )

            # Abort earthquake simulating and Update coordinator data
            coordinator_data["recent"]["simulating"] = {}
            self.coordinator.async_set_updated_data(coordinator_data)

        return True

    async def load_report_data(self, data: dict[str, Any] | None = None) -> bool:
        """Perform report data processing."""
        default_data = {
            "cache": [],
            "recent": {},
            "fetch_time": 0,
        }
        coordinator_data = self.coordinator.data

        # Load recent data from stored
        store_report = self.sotre_handler.get_store("report")
        store_data = await store_report.async_load()
        coordinator_data.setdefault("report", store_data or default_data)

        # Check earthquake data if not None
        if data:
            report_id = data["id"]

            # Adjust the report data format
            pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
            result = re.search(pattern, data.get("id", ""))
            if result:
                parts = result.groups()
                data["id"] = "-".join(parts)
                data.setdefault("author", "cwa")
            data.setdefault("author", "ExpTechTW")

            # Check earthquake data if not exist
            cache: list[dict[str, Any]] = coordinator_data["report"]["cache"]
            seen = {d["id"] for d in cache}
            if data["id"] in seen:
                return False

            # Stored earthquake data to runtime data
            data.update(await self.http_client.fetch_report_detail(report_id))
            coordinator_data["report"]["recent"] = data

            # Stored to report cache
            new_cache = cache.copy()
            new_cache.insert(0, data)
            coordinator_data["report"]["cache"] = new_cache[:5]
            await store_report.async_save(
                coordinator_data["report"],
            )

            # Update coordinator data
            self.coordinator.async_set_updated_data(coordinator_data)

        return True

    async def load_eew_data(self, newer_id: str | None = None) -> dict:
        """Get the report or latest earthquake data."""
        coordinator_data = self.coordinator.data
        eew_data: dict = coordinator_data["recent"]["earthquake"]
        simulate_data: dict = coordinator_data["recent"]["simulating"]
        report_data: dict = coordinator_data["report"]["recent"]
        intensity_data: dict = coordinator_data["recent"]["intensity"]

        # Return simulate data if simulating
        if simulate_data:
            simulate_data["intensity"], simulate_data["list"] = await self.load_intensitys(simulate_data)
            return simulate_data

        # Check if newer_id exists in the report cache, Or use the latest earthquake data ID
        if newer_id is None:
            newer_id = eew_data.get("id")
        else:
            for data in coordinator_data["report"]["cache"]:
                if data["id"] == newer_id:
                    report_data = data
                    break

            # If the report ID matches the earthquake data, return the earthquake data
            if newer_id == eew_data.get("id"):
                return eew_data

        # If the report data is newer than the earthquake data, update the earthquake data
        if report_data.get("time", 1) > eew_data.get("time", 0) or newer_id != eew_data.get("id"):
            eew_data["intensity"], eew_data["list"] = await self.load_intensitys(eew_data, report_data)
            eew_data["id"] = report_data.get("id")
            eew_data["author"] = report_data.get("author")
            eew_data.pop("serial", None)
            eq: dict = eew_data.get("eq", {})
            for key in ("lat", "lon", "depth", "loc", "mag", "time"):
                eq[key] = report_data.get(key)
            eq["max"] = report_data.get("int")
            eew_data["eq"] = eq
            eew_data["time"] = eq.get("time")
            eew_data["md5"] = report_data.get("md5")
            return eew_data

        # If the intensity data id does not match the report trem id
        if (id_ := intensity_data.get("id")) and id_ != report_data.get("trem"):
            intensitys = {}
            intensitys["intensity"], intensitys["list"] = await self.load_intensitys()
            intensitys["id"] = intensity_data.get("id")
            intensitys["author"] = intensity_data.get("author")
            intensitys["max"] = intensity_data.get("max")
            return intensitys

        return eew_data

    async def load_intensitys(
        self,
        eew: dict[str, Any] | None = None,
        report: dict[str, Any] | None = None,
    ) -> tuple[dict, dict]:
        """Get the latest intensity data.

        Returns
        -------
        intensity : dict
            intensitys used for map drawing
        lists : dict
            intensitys used for listing attributes

        """
        coordinator_data = self.coordinator.data

        if eew is None:
            eew = {}

        if report is None:
            report = {}

        eew_id = eew.get("id")
        intensity_data: dict = coordinator_data["recent"]["intensity"]
        report_intensity: dict | None = report.get("list")
        report_id = report.get("id")
        intensity = eew.get("intensity")
        lists = eew.get("lists")

        # Reset intensity id if not equal report id
        if eew_id != report_id:
            intensity_data.pop("id", None)

        # Case 1: Comparison of intensity and report data
        intensity_data.setdefault("id", report.get("trem"))
        if report_intensity and intensity_data.get("id") == report.get("trem"):
            county_list = {v: k for k, v in ATTR_COUNTY.items()}
            intensity = {county_list[county]: detail["int"] for county, detail in report_intensity.items()}
            lists = {
                key: intensity_to_text(details["int"])
                for county, details in report_intensity.items()
                for key in [county] + [f"{county}{town}" for town in details["town"]]
            }

            return intensity, lists

        # Case 2: Preferred intensity data
        intensity = intensity or await self.convert_zip3_county(intensity_data)
        lists = lists or await self.convert_zip3_town(intensity_data)

        return intensity, lists

    async def convert_zip3_county(self, intensitys: dict[str, Any]) -> dict:  # noqa: PLR6301
        """Convert ZIP Code to county id."""
        result = {}

        if "area" not in intensitys:
            return {}

        # Each intensity area
        intensity_area: dict[str, Any] = intensitys["area"]
        for i, j in intensity_area.items():
            # Each township
            for k in j:
                # Each county
                for county_id, (zip_start, zip_end) in COUNTY_TOWN.items():
                    # If township in county
                    if zip_start <= k <= zip_end:
                        # Only update if new intensity is higher
                        if county_id not in result or result[county_id] < int(i):
                            result[county_id] = int(i)
                        break

        return result

    async def convert_zip3_town(self, intensitys) -> dict:  # noqa: PLR6301
        """Convert ZIP Code to Township name."""
        result = {}

        if "area" not in intensitys:
            return {}

        # Each intensity area
        intensity_area: dict[str, Any] = intensitys["area"]
        for i, j in intensity_area.items():
            town = []
            for k in j:
                if k in ZIP3_TOWN:
                    town.insert(0, ZIP3_TOWN[k])
            result[intensity_to_text(int(i))] = town

        return result

    async def fetch_report(self):
        """Fetch report data detail."""
        coordinator_data = self.coordinator.data

        report_data = await self.http_client.fetch_report()
        for data in report_data:
            # Get report detail data
            report_data_detail = await self.http_client.fetch_report_detail(data["id"])
            data.update(report_data_detail)

            # Convert report id and fix missing author
            pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
            result = re.search(pattern, data.get("id", ""))
            if result:
                parts = result.groups()
                data["id"] = "-".join(parts)
                data.setdefault("author", "cwa")
            data.setdefault("author", "ExpTechTW")

        if report_data:
            coordinator_data["report"]["recent"] = report_data[0]
            coordinator_data["report"]["cache"] = report_data
            coordinator_data["report"]["fetch_time"] = datetime.now().timestamp()

            # Update coordinator data
            self.coordinator.async_set_updated_data(coordinator_data)

    async def api_node(self):
        """Return current connection mode."""
        if self.web_socket:
            if self.web_socket.fallback_mode:
                return ("http (fallback)", self.http_client.api_node)
            else:
                if self.web_socket.state.is_running:
                    return ("websocket", self.web_socket.api_node)

        return ("http", self.http_client.api_node)

    async def server_status(self, **kwargs):
        """Return current server status."""
        _, api_node = await self.api_node()

        return {
            "current_node": kwargs.get("node", api_node),
            "unavailable": kwargs.get("unavailable", []),
            "latency": await self._connection_latency(),
        }

    async def _connection_latency(self) -> float | str:
        """Return current latency."""
        update_interval = self.config_entry.runtime_data.update_interval.total_seconds()
        protocol, _ = await self.api_node()

        if self.web_socket and protocol.find("websocket") >= 0:
            latency = abs(
                self.web_socket.state.ping_time - self.web_socket.state.pong_time,
            )
        else:
            latency = self.http_client.latency + (update_interval if update_interval > 1 else 0)

        return f"{latency:.3f}" if latency < 6 else "6s+"

    @property
    def coordinator(self):
        return self.config_entry.runtime_data.coordinator

    @property
    def http_client(self):
        return self.config_entry.runtime_data.http_client

    @property
    def web_socket(self):
        return self.config_entry.runtime_data.web_socket

    @property
    def sotre_handler(self):
        return self.config_entry.runtime_data.sotre_handler
