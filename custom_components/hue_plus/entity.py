"""Gemeinsame Basis für alle Entitäten von LED Color (technischer Name: hue_plus)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .api import HueClient
from .const import DOMAIN


def bridge_device_info(client: HueClient) -> DeviceInfo:
    """Alle Entitäten hängen an EINEM Gerät «LED Color».

    So entstehen keine doppelten Lampen-Geräte neben denen der offiziellen
    Integration.
    """
    bridge = client.bridge
    bridge_id = bridge.get("bridge_id", client.host)
    return DeviceInfo(
        identifiers={(DOMAIN, bridge_id)},
        name="LED Color",
        manufacturer="Signify (inoffiziell erweitert durch LED Color)",
        model="Hue Bridge",
        configuration_url=f"https://{client.host}",
    )


class HuePlusEntity(Entity):
    """Entität, die einer Ressource der Bridge folgt."""

    _attr_should_poll = False
    # Name = Gerätename «LED Color» + eigener Name, z. B. «LED Color Signe L Verlauf»
    _attr_has_entity_name = True

    def __init__(self, client: HueClient, resource: dict[str, Any]) -> None:
        """Entität für eine Ressource anlegen."""
        self.client = client
        self.rid: str = resource["id"]
        self.rtype: str = resource["type"]
        self._attr_device_info = bridge_device_info(client)

    def link_to_hue_device(self, hass: HomeAssistant, hue_id: str | None) -> bool:
        """Entität beim passenden Gerät der OFFIZIELLEN Hue-Integration anzeigen.

        Z. B. «Einschaltverhalten» direkt bei der Lampe. Es wird kein neues Gerät angelegt. Gibt es das Gerät
        (noch) nicht, bleibt die Entität beim Sammel-Gerät «LED Color».
        """
        if not hue_id:
            return False
        device = dr.async_get(hass).async_get_device(identifiers={("hue", hue_id)})
        if device is None:
            return False
        self._attr_device_info = None
        self.device_entry = device
        return True

    def set_entity_id(self, platform: str, name: str) -> None:
        """Feste, gleichbleibende Entitäts-ID «<plattform>.hue_plus_<name>».

        Gilt nur für NEUE Entitäten; bestehende behalten ihre ID.
        """
        self.entity_id = f"{platform}.hue_plus_{slugify(name)}"

    @property
    def resource(self) -> dict[str, Any]:
        """Aktueller Stand der Ressource (leer, wenn gelöscht)."""
        return self.client.get(self.rid) or {}

    @property
    def available(self) -> bool:
        """Verfügbar, solange die Bridge verbunden ist und die Ressource existiert."""
        return self.client.connected and self.rid in self.client.resources

    async def async_added_to_hass(self) -> None:
        """Bei Änderungen dieser Ressource neu zeichnen."""
        self.async_on_remove(self.client.subscribe(self._handle_event, self.rid))

    @callback
    def _handle_event(self, event_type: str, resource: dict[str, Any] | None) -> None:
        self._update_from_resource()
        self.async_write_ha_state()

    @callback
    def _update_from_resource(self) -> None:
        """Wird in Unterklassen überschrieben (z. B. Name nachführen)."""
