"""Register Data Classes for TREM2 component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from .update_coordinator import Trem2UpdateCoordinator


@dataclass
class Trem2RuntimeData:
    """Class to help runtime data."""

    name: str
    coordinator: Trem2UpdateCoordinator
    recent_sotre: Store
    report_store: Store
    platforms: list[Platform]
