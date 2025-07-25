"""Initialize the platform for TREM2 component."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import subprocess

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.http_client import ExpTechHTTPClient
from .api.web_socket import ExpTechWSClient
from .const import (
    BASE_INTERVAL,
    BASE_PLATFORMS,
    CONF_AGREE,
    DOMAIN,
    FAST_INTERVAL,
    PARAMS_OPTIONS,
    PROVIDER_OPTIONS,
    STARTUP,
)
from .runtime import Trem2RuntimeData
from .services import async_register_services
from .store import StoreHandler
from .update_coordinator import Trem2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)


type Trem2ConfigEntry = ConfigEntry[Trem2RuntimeData]


async def async_setup_entry(hass: HomeAssistant, config_entry: Trem2ConfigEntry) -> bool:
    """Set up platforms from a config entry."""
    http_client: ExpTechHTTPClient
    web_socket: ExpTechWSClient | None = None

    # Migrate data (also after first setup) to options
    if config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data={}, options=config_entry.data)

    # Check Terms of Service acceptance
    if not config_entry.options.get(CONF_AGREE, False):
        raise ConfigEntryError("You must review the latest and accept the Terms of Service to use this integration.")

    # Get client session
    session = async_get_clientsession(hass)

    # Store the config entry data in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})

    # Refresh entry when a options is update
    config_entry.add_update_listener(async_update_options)

    # Initialization http client
    platforms = BASE_PLATFORMS.copy()
    http_client = ExpTechHTTPClient(
        config_entry=config_entry,
        hass=hass,
        session=session,
    )
    await http_client.initialize_route()
    update_interval = BASE_INTERVAL

    # Initialization websocket client
    if CONF_API_TOKEN in config_entry.options:
        platforms.insert(0, Platform.BINARY_SENSOR)
        web_socket = ExpTechWSClient(
            config_entry=config_entry,
            hass=hass,
            session=session,
            access_token=config_entry.options[CONF_API_TOKEN],
        )
        await web_socket.initialize_route()
        update_interval = FAST_INTERVAL

        # Set up the WebSocket client
        try:
            await web_socket.connect()
        except RuntimeError as ex:
            raise ConfigEntryNotReady from ex

    # Setup config entry options to params
    def get_provider_option(key, val):
        if key == "type":
            for k, v in PROVIDER_OPTIONS:
                if k == val:
                    return v
        return val

    # Set up the runtime and coordinator
    config_options = getattr(config_entry, "options", {})
    params = {k: get_provider_option(k, v) for k, v in config_options.items() if k in PARAMS_OPTIONS and v}
    update_coordinator = Trem2UpdateCoordinator(
        hass,
        config_entry,
    )
    store_handler = StoreHandler(hass, config_entry)
    store_handler.setup_stores()
    config_entry.runtime_data = Trem2RuntimeData(
        coordinator=update_coordinator,
        sotre_handler=store_handler,
        platforms=platforms,
        http_client=http_client,
        web_socket=web_socket,
        params=params,
        update_interval=update_interval,
    )

    # Set up the platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, platforms)

    # Refresh data for coordinator when a config entry is setup
    await update_coordinator.async_config_entry_first_refresh()

    # Setup coordinator data
    update_coordinator.data = {}
    await update_coordinator.data_client.load_recent_data()
    await update_coordinator.data_client.load_report_data()
    await update_coordinator.data_client.fetch_report()

    # Install fonts if not already installed
    await async_setup_extra(hass)

    # Display startup message
    _LOGGER.info(STARTUP)
    return True


async def async_setup_extra(hass: HomeAssistant) -> None:
    """Install service and fonts if not already installed."""
    service_key = f"{DOMAIN}_simulate_registered"
    font_key = f"{DOMAIN}_font_checked"

    if service_key not in hass.data[DOMAIN]:
        hass.data[DOMAIN][service_key] = await async_register_services(hass)

    if font_key in hass.data[DOMAIN]:
        return

    hass.data[DOMAIN][font_key] = True
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

    # Check if the user has the fonts installed
    for name, path in fonts_list.items():
        if not check_font(name):
            _LOGGER.info("Font %s not found. Installing", name)
            await install_font(hass.config.path(path))


async def async_update_options(hass: HomeAssistant, config_entry: Trem2ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: Trem2ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data: dict = hass.data[DOMAIN]
    runtime_data = config_entry.runtime_data
    coordinator = runtime_data.coordinator

    # Stored coordinator data
    recent_data = coordinator.data["recent"]
    recent_store = runtime_data.sotre_handler.get_store("recent")
    if recent_data and recent_store:
        await recent_store.async_save(recent_data)

    report_data = coordinator.data["report"]
    report_store = runtime_data.sotre_handler.get_store("report")
    if report_data and report_store:
        await report_store.async_save(report_data)

    # Unload platforms
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    config_entry,
                    platform,
                )
                for platform in config_entry.runtime_data.platforms
            ]
        )
    )

    if unload_ok:
        domain_data.pop(config_entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: Trem2ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
