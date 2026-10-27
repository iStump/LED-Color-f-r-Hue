"""Eigene Seite «LED Color» in der Seitenleiste von Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "led-color"
STATIC_URL = "/hue_plus_static"
_DATA_STATIC = f"{DOMAIN}_static_registered"
_DATA_PANEL = f"{DOMAIN}_panel_registered"
_DATA_EXTRA = f"{DOMAIN}_extra_js"
# Eigener Eintrag unter Dashboards → Ressourcen. Ressourcen lädt Home Assistant erst, wenn
# es fertig gestartet ist – so ist die Karte «custom:led-color-card» immer bekannt.
RESOURCE_PATH = f"{STATIC_URL}/led-color-panel.js"
RESOURCE_MARK = "karte=1"


def _resources(hass: HomeAssistant):
    """Ressourcen-Liste der Dashboards (nur im normalen UI-Modus, nicht bei YAML)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415
    except ImportError:  # sehr alte Versionen
        return None
    data = hass.data.get(LOVELACE_DATA)
    resources = getattr(data, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


def _ours(item: dict) -> bool:
    return str(item.get("url", "")).startswith(RESOURCE_PATH) and RESOURCE_MARK in str(item.get("url"))


async def async_ensure_resource(hass: HomeAssistant, version: str) -> None:
    """Karte als Dashboard-Ressource eintragen (bzw. auf die neue Version stellen)."""
    resources = _resources(hass)
    if resources is None:
        return
    url = f"{RESOURCE_PATH}?v={version}&{RESOURCE_MARK}"
    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        mine = [item for item in resources.async_items() if _ours(item)]
        for extra in mine[1:]:
            await resources.async_delete_item(extra["id"])
        if not mine:
            await resources.async_create_item({"res_type": "module", "url": url})
        elif mine[0].get("url") != url:
            await resources.async_update_item(mine[0]["id"], {"res_type": "module", "url": url})
    except Exception:  # noqa: BLE001 – darf den Start nie verhindern
        _LOGGER.warning("LED Color: Dashboard-Ressource konnte nicht eingetragen werden", exc_info=True)


async def async_remove_resource(hass: HomeAssistant) -> None:
    """Eintrag wieder entfernen (wenn LED Color gelöscht wird)."""
    resources = _resources(hass)
    if resources is None:
        return
    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        for item in [i for i in resources.async_items() if _ours(i)]:
            await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001
        _LOGGER.debug("LED Color: Ressource nicht entfernt", exc_info=True)


async def async_register_panel(hass: HomeAssistant, version: str) -> None:
    """Seite anmelden (nur einmal, auch bei mehreren Bridges)."""
    if not hass.data.get(_DATA_STATIC):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL, str(Path(__file__).parent / "frontend"), cache_headers=False
                )
            ]
        )
        hass.data[_DATA_STATIC] = True
    if hass.data.get(_DATA_PANEL):
        return
    await async_ensure_resource(hass, version)
    # Dieselbe Datei auf allen Seiten laden: so gibt es die Karte
    # «custom:led-color-card» in jedem Dashboard, ohne Ressource von Hand.
    url = f"{STATIC_URL}/led-color-panel.js?v={version}"
    if not hass.data.get(_DATA_EXTRA):
        frontend.add_extra_js_url(hass, url)
        hass.data[_DATA_EXTRA] = url
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="led-color-panel",
        sidebar_title="LED Color",
        sidebar_icon="mdi:gradient-horizontal",
        # ?v=… sorgt dafür, dass nach einem Update sofort die neue Seite geladen wird
        module_url=url,
        require_admin=False,
        config={"version": version},
    )
    hass.data[_DATA_PANEL] = True


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Seite entfernen (wenn keine Bridge mehr eingerichtet ist)."""
    if hass.data.pop(_DATA_PANEL, False):
        frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
