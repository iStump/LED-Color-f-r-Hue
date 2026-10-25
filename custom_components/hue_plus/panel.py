"""Eigene Seite «LED Color» in der Seitenleiste von Home Assistant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = "led-color"
STATIC_URL = "/hue_plus_static"
_DATA_STATIC = f"{DOMAIN}_static_registered"
_DATA_PANEL = f"{DOMAIN}_panel_registered"
_DATA_EXTRA = f"{DOMAIN}_extra_js"


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
