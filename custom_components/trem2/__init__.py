"""Initialize the platform for TREM2 component."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import subprocess

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    PLATFORMS,
    STARTUP,
    STORAGE_EEW,
    STORAGE_REPORT,
    TREM2_COORDINATOR,
    TREM2_NAME,
    UPDATE_LISTENER,
)
from .services import async_register_services
from .update_coordinator import trem2_update_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Custom Image Display from a config entry."""
    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data={}, options=entry.data)

    # Store the config entry data in hass.data
    hass.data.setdefault(DOMAIN, {})
    domain_data: dict = {}

    store_eew = Store(hass, 1, STORAGE_EEW)
    store_report = Store(hass, 1, STORAGE_REPORT)
    update_coordinator = trem2_update_coordinator(
        hass,
        store_eew,
        store_report,
    )
    domain_data = {
        TREM2_COORDINATOR: update_coordinator,
        TREM2_NAME: DEFAULT_NAME,
    }

    # Set up the coordinator
    await update_coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = domain_data

    # Set up the coordinator listener
    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener

    # Set up the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    assets_path = f"custom_components/{DOMAIN}/assets"
    font_name = "Noto Sans TC"
    font_path = hass.config.path(f"{assets_path}/NotoSansTC-Regular.ttf")

    def check_font(font_name: str) -> bool:
        """Check if font is installed."""
        try:
            fc_list = subprocess.Popen(
                ["fc-list", ":family"],
                stdout=subprocess.PIPE,
                text=True,
            )
            grep = subprocess.Popen(
                ["grep", font_name],
                stdin=fc_list.stdout,
                stdout=subprocess.PIPE,
                text=True,
            )
            fc_list.stdout.close()
            output, _ = grep.communicate()

            return bool(output.strip())
        except subprocess.CalledProcessError as e:
            _LOGGER.error("Error checking font: %s", e)

        return False

    async def get_user_font_dir() -> Path:
        """Get the user font directory."""
        font_dir = Path.home() / ".local/share/fonts"
        font_dir.mkdir(parents=True, exist_ok=True)

        return font_dir

    async def install_font(font_path: str):
        """Install a font by copying into the user font directory and updating cache."""
        try:
            # Create font cache directory if it doesn't exist
            user_font_dir = await get_user_font_dir()
            font_dest = user_font_dir / Path(font_path).name

            # Copy the font file to the cache directory
            process = await asyncio.create_subprocess_exec(
                "cp",
                font_path,
                str(font_dest),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            # Update the font cache
            process = await asyncio.create_subprocess_exec(
                "fc-cache",
                "-fv",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
        except subprocess.CalledProcessError as e:
            _LOGGER.error("Error installing font: %s", e)

    if not check_font(font_name):
        _LOGGER.info("Font %s not found. Installing", font_name)
        await install_font(font_path)

    # Register actions
    await async_register_services(hass, update_coordinator)

    _LOGGER.info(STARTUP)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS]
        )
    )

    if unload_ok:
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
