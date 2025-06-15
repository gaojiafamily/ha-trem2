from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFINED_STORES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class StoreHandler:
    """Manages the lifecycle of all storage instances for a config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Store Handler."""
        self._hass = hass
        self._config_entry = config_entry
        self.stores: dict[str, Store] = {}

    def setup_stores(self):
        """Create all defined Store instances based on the central configuration."""
        for name, definition in DEFINED_STORES.items():
            key = definition.key_template.format(
                domain=DOMAIN,
                entry_id=self._config_entry.entry_id,
            )
            store = Store(self._hass, definition.version, key)
            self.stores[name] = store
            _LOGGER.debug("Initialized store '%s' with key: %s", name, key)

    def get_store(self, name: str) -> Store:
        """Get a specific store instance by its friendly name."""
        return self.stores[name]
