"""Processing Data for TREM2 component."""

from __future__ import annotations

from datetime import datetime
from logging import Logger
import re
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import ATTR_COUNTY, COUNTY_TOWN, ZIP3_TOWN
from .core.earthquake import intensity_to_text

if TYPE_CHECKING:
    from .runtime import Trem2RuntimeData

type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


class Trem2Store:
    """Defines stored for TREM2."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        config_entry: Trem2ConfigEntry,
    ) -> None:
        """Initialize the stored."""
        self.hass = hass
        self.logger = logger
        self.config_entry = config_entry
        self.coordinator_data = {}

    async def load_recent_data(self, data: dict[str, Any] | None = None) -> bool:
        """Perform recent data processing."""
        default_data = {
            "cache": [],
            "earthquake": {},
            "intensity": {},
            "tsunami": {},
            "simulating": {},
        }

        # Load recent data from stored
        if "recent" not in self.coordinator_data:
            store_eew: Store = self.config_entry.runtime_data.recent_sotre
            store_data = await store_eew.async_load()
            self.coordinator_data["recent"] = store_data or default_data

        # Check earthquake data if not None
        if data:
            try:
                cache: list[dict[str, Any]] = self.coordinator_data["recent"]["cache"].copy()
                seen = {(d["id"], d.get("serial", "")) for d in cache}
                key = (data["id"], data.get("serial", ""))
                if key in seen:
                    return False
            except KeyError as e:
                self.logger.error(e)

            # Stored earthquake data to runtime data
            coordinator = self.config_entry.runtime_data.coordinator
            data.pop("type", None)
            data.setdefault("time", data.get("time", 0))
            provider = coordinator.conf.params.get("type")
            if provider == "" or data.get("author") == provider:
                self.coordinator_data["recent"]["earthquake"] = data

            # Stored to earthquake cache
            cache.insert(0, data)
            self.coordinator_data["recent"]["cache"] = cache[-10:]
            await self.config_entry.runtime_data.recent_sotre.async_save(
                self.coordinator_data["recent"],
            )

            # Abort earthquake simulating
            self.coordinator_data["recent"]["simulating"] = {}

        return True

    async def load_report_data(self, data: dict[str, Any] | None = None) -> bool:
        """Perform report data processing."""
        default_data = {
            "cache": [],
            "recent": {},
            "fetch_time": 0,
        }

        # Load recent data from stored
        if "report" not in self.coordinator_data:
            store_report: Store = self.config_entry.runtime_data.report_store
            store_data = await store_report.async_load()
            self.coordinator_data["report"] = store_data or default_data

        # Check earthquake data if not None
        if data:
            report_id = data["id"].copy()

            # Adjust the report data format
            pattern = r"(\d{6})-?(?:\d{4})-([0-1][0-9][0-3][0-9])-(\d{6})"
            result = re.search(pattern, data.get("id", ""))
            if result:
                parts = result.groups()
                data["id"] = "-".join(parts)
                data.setdefault("author", "cwa")
            data.setdefault("author", "ExpTechTW")

            # Check earthquake data if not exist
            cache: list[dict[str, Any]] = self.coordinator_data["report"]["cache"].copy()
            seen = {d["id"] for d in cache}
            if data["id"] in seen:
                return False

            # Stored earthquake data to runtime data
            coordinator = self.config_entry.runtime_data.coordinator
            data.update(await coordinator.client.http.fetch_report_detail(report_id))
            self.coordinator_data["report"]["recent"] = data

            # Stored to report cache
            cache.insert(0, data)
            self.coordinator_data["report"]["cache"] = cache[-5:]
            await self.config_entry.runtime_data.report_store.async_save(
                self.coordinator_data["report"],
            )

        return True

    async def load_eew_data(self, report_id: str | None = None) -> dict:
        """Get the report or latest earthquake data."""
        coordinator = self.config_entry.runtime_data.coordinator
        eew_data: dict = coordinator.data["recent"]["earthquake"]
        simulate_data: dict = coordinator.data["recent"]["simulating"]
        report_data: dict = coordinator.data["report"]["recent"]

        # Return simulate data if simulating
        if simulate_data:
            return simulate_data

        # Return report data if selected
        if report_id:
            for data in coordinator.data["report"]["cache"]:
                if data["id"] == report_id:
                    report_data = data
                    break

            # If the report ID matches the earthquake data, return the earthquake data
            if report_id == eew_data.get("id"):
                return eew_data
        else:
            report_id = eew_data.get("id")

        # If the report data is newer than the earthquake data, update the earthquake data
        if report_data.get("time", 1) > eew_data.get("time", 0) or report_id != eew_data.get("id"):
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

    async def load_intensitys(
        self,
        eew: dict | None = None,
        report: dict | None = None,
    ) -> tuple[dict, dict]:
        """Get the latest intensity data.

        Returns
        -------
        intensity : dict
            intensitys used for map drawing
        lists : dict
            intensitys used for listing attributes

        """
        if eew is None:
            eew = {}

        if report is None:
            report = {}

        eew_id = eew.get(id)
        intensitys_data: dict = self.coordinator_data["recent"]["intensity"]
        report_intensity: dict | None = report.get("list")
        report_id = report.get("id")

        # 當報表不同時，重設震度速報 ID
        if eew_id != report_id:
            intensitys_data.pop("id", None)

        # Case 1: 比對震度速報和報表資料
        intensitys_data.setdefault("id", report.get("trem"))
        if report_intensity and intensitys_data.get("id") == report.get("trem"):
            county_list = {v: k for k, v in ATTR_COUNTY.items()}
            intensity = {county_list[county]: detail["int"] for county, detail in report_intensity.items()}
            lists = {
                key: intensity_to_text(details["int"])
                for county, details in report_intensity.items()
                for key in [county] + [f"{county}{town}" for town in details["town"]]
            }

            return intensity, lists

        # Case 2: 使用震度速報資料為主
        intensity = await self.convert_zip3_county(intensitys_data)
        lists = await self.convert_zip3_town(intensitys_data)

        return intensity, lists

    async def convert_zip3_county(self, intensitys) -> dict:  # noqa: PLR6301
        """Convert ZIP Code to county id."""
        result = {}

        if "area" not in intensitys:
            return {}

        # Each intensity area
        for i, j in intensitys["area"].items():
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

        for i, j in intensitys["area"].items():
            town = []
            for k in j:
                if k in ZIP3_TOWN:
                    town.insert(0, ZIP3_TOWN[k])
            result[intensity_to_text(int(i))] = town

        return result

    async def fetch_report(self):
        """Fetch report data detail."""
        coordinator = self.config_entry.runtime_data.coordinator

        report_data = await coordinator.client.http.fetch_report()
        for data in report_data:
            # Get report detail data
            report_data_detail = await coordinator.client.http.fetch_report_detail(data["id"])
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
            self.coordinator_data["report"]["recent"] = report_data[0]
            self.coordinator_data["report"]["cache"] = report_data
            self.coordinator_data["report"]["fetch_time"] = datetime.now().timestamp()
