"""Runtime Data Class for TREM2 component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession
from pydantic import AnyUrl, RootModel, field_validator

from .enums import WebSocketService
from .runtime import WebSocketState


class EndPoint(RootModel[AnyUrl]):
    """
    A Pydantic model that validates a URL is either HTTP(s) or WebSocket(s).
    This model wraps a single AnyUrl object, allowing for direct instantiation.
    """

    @field_validator("root")
    @classmethod
    def check_supported_schemes(cls, v: AnyUrl) -> AnyUrl:
        """Ensure the URL scheme is in the list of supported schemes."""
        ALLOWED_SCHEMES = {"http", "https", "ws", "wss"}
        if v.scheme not in ALLOWED_SCHEMES:
            raise ValueError(f"Unsupported URL scheme '{v.scheme}'.")
        return v

    @property
    def is_websocket(self) -> bool:
        """Returns True if the URL is a WebSocket (ws:// or wss://)."""
        return self.root.scheme in {"ws", "wss"}

    @property
    def is_http(self) -> bool:
        """Returns True if the URL is an HTTP URL (http:// or https://)."""
        return self.root.scheme in {"http", "httpss"}

    @property
    def internal_url_object(self) -> AnyUrl:
        """Returns the internal Pydantic AnyUrl object."""
        return self.root

    def __str__(self) -> str:
        """Returns the URL as a string."""
        return str(self.root)

    def __repr__(self) -> str:
        """Provides a developer-friendly representation of the object."""
        return f"EndPoint('{str(self.root)}')"


@dataclass(kw_only=True, slots=True)
class ExpTechClient:
    """Initialize the client."""

    # Configuration set at initialization
    session: ClientSession
    api_node: str | None = None
    base_url: EndPoint | None = None
    node_cycler: DictKeyExclusionCycler
    retry_backoff = 0
    unavailables: list[str] | None = None

    # Required only for WebSocket connections.
    fallback_mode = False
    register_service = [
        WebSocketService.CWA_INTENSITY,
        WebSocketService.EEW,
        WebSocketService.REPORT,
        WebSocketService.TREM_INTENSITY,
        WebSocketService.TSUNAMI,
    ]
    state = WebSocketState()


@dataclass
class StoreDefinition:
    """A dataclass to hold the configuration blueprint for a single Store instance."""

    version: int
    key_template: str


class DictKeyExclusionCycler:
    """A cycler that can dynamically exclude items from a dictionary based on their keys."""

    def __init__(
        self,
        data: dict[str, Any],
        exclude_keys: list[str] | None = None,
    ) -> None:
        """
        Initializes the cycler with a dictionary.

        Args:
            data: The dictionary of items to cycle through.
            exclude_keys: A list of keys to exclude from the cycle.
        """
        if not data:
            raise ValueError("Input dictionary cannot be empty.")

        self._data = data
        self._keys = list(self._data.keys())  # The order is guaranteed in Python 3.7+

        # The set of excluded keys for efficient lookups.
        self._excluded_keys: set[str] = set(exclude_keys or [])

        self._current_index = -1  # Start at -1 to begin with index 0 on the first call.

    def update_exclusions(self, new_exclude_keys: list[str]):
        """
        Allows updating the set of excluded keys at runtime.

        Args:
            new_exclude_keys: The new list of keys to exclude.
        """
        self._excluded_keys = set(new_exclude_keys)

    def next(self) -> tuple[Any, Any]:
        """Finds and returns the next valid key-value pair in the cycle."""
        # Safety check to prevent infinite loops if all items are excluded.
        if len(self._excluded_keys) >= len(self._keys):
            return (None, None)

        num_keys = len(self._keys)
        # Loop at most num_keys times to find the next valid item.
        for _ in range(num_keys):
            # Use the modulo operator to cycle the index.
            self._current_index = (self._current_index + 1) % num_keys

            current_key = self._keys[self._current_index]

            # Check if the current key is in the exclusion set.
            if current_key not in self._excluded_keys:
                # If not excluded, get the value and return the pair.
                current_value = self._data[current_key]
                return (current_key, current_value)

        # This part should not be reached if the check at the start is correct,
        # but serves as a safeguard.
        return (None, None)
