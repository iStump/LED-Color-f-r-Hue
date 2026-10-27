"""LED Color (technischer Name hue_plus) – ergänzt die offizielle Hue-Integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import HueAuthError, HueClient, HueError
from .const import CONF_APP_KEY, DOMAIN
from .panel import async_register_panel, async_remove_resource, async_unregister_panel
from .services import async_setup_services
from .websocket import async_setup_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type HuePlusConfigEntry = ConfigEntry[HueClient]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Aktionen und die Befehle für die Seite «LED Color» anmelden."""
    async_setup_services(hass)
    async_setup_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HuePlusConfigEntry) -> bool:
    """Verbindung zur Bridge aufbauen."""
    # Umbenennung «Hue Plus»/«Hue Pro» -> «LED Color für Hue» (nur wenn der Titel noch der alte ist)
    for old_name in ("Hue Plus", "Hue Pro"):
        if entry.title.startswith(old_name):
            hass.config_entries.async_update_entry(
                entry, title=entry.title.replace(old_name, "LED Color für Hue", 1)
            )
    session = async_get_clientsession(hass, verify_ssl=False)
    client = HueClient(session, entry.data[CONF_HOST], entry.data[CONF_APP_KEY])
    try:
        await client.async_refresh()
    except HueAuthError as err:
        raise ConfigEntryAuthFailed(
            "Die Bridge kennt LED Color nicht mehr – bitte neu koppeln"
        ) from err
    except HueError as err:
        raise ConfigEntryNotReady(
            f"Hue Bridge {entry.data[CONF_HOST]} nicht erreichbar: {err}"
        ) from err

    client.connected = True
    entry.runtime_data = client
    _remove_retired_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remove_empty_hub_device(hass, entry)
    await async_register_panel(hass, await _version(hass))

    client.start(
        lambda coro, name: entry.async_create_background_task(hass, coro, name),
        on_auth_failed=lambda: entry.async_start_reauth(hass),
    )
    entry.async_on_unload(client.stop)
    return True


async def _version(hass: HomeAssistant) -> str:
    """Versionsnummer aus manifest.json (für das Neuladen der Seite nach Updates)."""
    integration = await async_get_integration(hass, DOMAIN)
    return str(integration.version or "0")


def _remove_retired_entities(hass: HomeAssistant, entry: HuePlusConfigEntry) -> None:
    """Empfindlichkeits-Regler (bis 0.4.0) entfernen – die Hue App kann das selbst."""
    ent_reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if ent.domain == "number" and ent.unique_id.endswith("_empfindlichkeit"):
            ent_reg.async_remove(ent.entity_id)


def _remove_empty_hub_device(hass: HomeAssistant, entry: HuePlusConfigEntry) -> None:
    """Sammel-Gerät «LED Color» entfernen, wenn alle Entitäten bei Hue-Geräten hängen."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if not any(ident[0] == DOMAIN for ident in device.identifiers):
            continue  # Gerät der offiziellen Integration – nicht anfassen
        if not er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=True):
            dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HuePlusConfigEntry) -> bool:
    """LED Color entladen."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    others = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
    ]
    if unloaded and not others:
        async_unregister_panel(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: HuePlusConfigEntry) -> None:
    """LED Color wird gelöscht: den Eintrag unter Dashboards → Ressourcen mitnehmen."""
    if not [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]:
        await async_remove_resource(hass)
