"""Initialize the platform for TREM2 component."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import subprocess

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    PLATFORMS,
    STARTUP,
    UPDATE_COORDINATOR,
    UPDATE_LISTENER,
)
from .update_coordinator import Trem2UpdateCoordinator
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Custom Image Display from a config entry."""
    # Migrate data (also after first setup) to options
    if config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data={}, options=config_entry.data)

    # Store the config entry data in hass.data
    hass.data.setdefault(DOMAIN, {})

    # Refresh data for coordinator when a config entry is setup
    update_coordinator = Trem2UpdateCoordinator(
        hass,
    )
    await update_coordinator.async_config_entry_first_refresh()

    # Set up the update listener and coordinator params
    update_listener = config_entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][config_entry.entry_id] = {
        CONF_NAME: DEFAULT_NAME,
        UPDATE_COORDINATOR: update_coordinator,
        UPDATE_LISTENER: update_listener,
        "platforms": PLATFORMS.copy(),
    }

    # Set up the platforms
    platforms: list = hass.data[DOMAIN][config_entry.entry_id]["platforms"]
    if CONF_API_TOKEN not in config_entry.options and "binary_sensor" in platforms:
        platforms.remove("binary_sensor")
    await hass.config_entries.async_forward_entry_setups(config_entry, platforms)

    # Register services
    key = f"{DOMAIN}_simulate_registered"
    if not hass.data[DOMAIN].get(key):
        hass.data[DOMAIN][key] = await async_register_services(hass)

    # Install fonts if not already installed
    await async_font_install(hass)

    # Display startup message
    _LOGGER.info(STARTUP)
    return True


async def async_font_install(hass: HomeAssistant) -> None:
    """Install fonts if not already installed."""
    key = f"{DOMAIN}_font_checked"

    if hass.data[DOMAIN].get(key):
        return

    hass.data[DOMAIN][key] = True
    assets_path = f"custom_components/{DOMAIN}/assets"
    fonts_list = {
        "Noto Sans TC": f"{assets_path}/NotoSansTC-Regular.ttf",
        "Noto Sans SC": f"{assets_path}/NotoSansSC-Regular.ttf",
        "Noto Sans JP": f"{assets_path}/NotoSansJP-Regular.ttf",
    }

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
            if fc_list.stdout:
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

    # Check if the user has the fonts installed-2
    for name, path in fonts_list.items():
        if not check_font(name):
            _LOGGER.info("Font %s not found. Installing", name)
            await install_font(hass.config.path(path))


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data: dict = hass.data[DOMAIN]
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    config_entry,
                    platform,
                )
                for platform in domain_data[config_entry.entry_id]["platforms"]
            ]
        )
    )

    if unload_ok:
        domain_data.pop(config_entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
