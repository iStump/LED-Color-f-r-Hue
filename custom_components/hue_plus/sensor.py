"""Sensor «Verlauf» für jede Hue-Lampe mit Farbverlauf (Gradient)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HuePlusConfigEntry
from .api import HueClient
from .colors import light_colors
from .const import (
    ATTR_AN,
    ATTR_EFFEKT,
    ATTR_ERREICHBAR,
    ATTR_FARBEN,
    ATTR_HELLIGKEIT,
    ATTR_LICHT_ID,
    ATTR_MODI,
    ATTR_MODUS,
    ATTR_PIXEL,
    ATTR_PUNKTE_MAX,
    ATTR_SYNC,
)
from .entity import HuePlusEntity

PARALLEL_UPDATES = 0


def is_gradient_light(resource: dict[str, Any]) -> bool:
    """Signe, Gradient Lightstrip, Play Gradient … haben ein «gradient»-Feld."""
    return resource.get("type") == "light" and isinstance(resource.get("gradient"), dict)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HuePlusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Verlauf-Sensoren anlegen – auch für später hinzugefügte Lampen."""
    client = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new(*_: Any) -> None:
        new = [
            HueGradientSensor(hass, client, light)
            for light in client.of_type("light")
            if is_gradient_light(light) and light["id"] not in known
        ]
        known.update(e.rid for e in new)
        if new:
            async_add_entities(new)

    _add_new()

    @callback
    def _on_event(event_type: str, resource: dict[str, Any] | None) -> None:
        if event_type in ("add", "refresh") or (
            event_type == "update"
            and resource is not None
            and resource.get("id") not in known
            and is_gradient_light(resource)
        ):
            _add_new()

    entry.async_on_unload(client.subscribe(_on_event))


class HueGradientSensor(HuePlusEntity, SensorEntity):
    """Zeigt alle Farbpunkte eines Verlaufs.

    Zustand: die Farben als Text, z. B. «#2f63ff, #16b8f0, #ff8a00».
    Attribute (stabil, das Dashboard liest sie):
      farben      – Liste von Hex-Farben in Reihenfolge
      modus       – interpolated_palette, segmented_palette, … oder «einfarbig»
      helligkeit  – 0–100 (%)
      an          – true/false
      erreichbar  – false, wenn die Lampe stromlos ist (Wandschalter aus)
      sync_aktiv  – true, solange Hue Sync / Entertainment die Lampe steuert
    """

    _attr_translation_key = "verlauf"
    _unrecorded_attributes = frozenset(
        {ATTR_MODI, ATTR_PUNKTE_MAX, ATTR_PIXEL, ATTR_LICHT_ID}
    )

    def __init__(
        self, hass: HomeAssistant, client: HueClient, resource: dict[str, Any]
    ) -> None:
        """Sensor für eine Gradient-Lampe."""
        super().__init__(client, resource)
        self._attr_unique_id = f"{self.rid}_verlauf"
        # bei der Lampe selbst anzeigen (Name dann: «<Lampe> Verlauf»)
        self._linked = self.link_to_hue_device(hass, resource.get("owner", {}).get("rid"))
        self._update_from_resource()
        self.set_entity_id("sensor", f"{self.client.name_of(resource) or 'lampe'}_verlauf")

    async def async_added_to_hass(self) -> None:
        """Zusätzlich auf Erreichbarkeit und Sync (Entertainment) hören."""
        await super().async_added_to_hass()
        self.async_on_remove(self.client.subscribe(self._handle_related))

    @callback
    def _handle_related(self, event_type: str, resource: dict[str, Any] | None) -> None:
        if resource is None:
            return
        if resource.get("type") == "entertainment_configuration" or (
            resource.get("id") == self._connectivity_rid()
        ):
            self.async_write_ha_state()

    def _connectivity_rid(self) -> str | None:
        """ID der Zigbee-Verbindung des Geräts, zu dem diese Lampe gehört."""
        device = self.client.get(self.resource.get("owner", {}).get("rid"))
        for service in (device or {}).get("services", []):
            if service.get("rtype") == "zigbee_connectivity":
                return service.get("rid")
        return None

    def _reachable(self) -> bool | None:
        """True = Lampe antwortet, False = stromlos/nicht erreichbar, None = unbekannt."""
        conn = self.client.get(self._connectivity_rid())
        if not conn:
            return None
        return conn.get("status") not in ("disconnected", "connectivity_issue")

    def _sync_active(self) -> bool:
        """Läuft gerade Hue Sync / Entertainment mit dieser Lampe?"""
        for config in self.client.of_type("entertainment_configuration"):
            if config.get("status") != "active":
                continue
            if any(s.get("rid") == self.rid for s in config.get("light_services") or []):
                return True
        return False

    @callback
    def _update_from_resource(self) -> None:
        if self._linked:
            return  # Name kommt vom Lampen-Gerät + «Verlauf»
        name = self.client.name_of(self.resource) or "Hue Lampe"
        self._attr_name = f"{name} Verlauf"

    @property
    def native_value(self) -> str | None:
        """Farben als kurzer Text."""
        colors, _ = light_colors(self.resource)
        return ", ".join(colors)[:255] if colors else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Alle Details zum Verlauf."""
        light = self.resource
        colors, mode = light_colors(light)
        gradient = light.get("gradient") or {}
        brightness = light.get("dimming", {}).get("brightness")
        effect = None
        for key in ("effects_v2", "effects", "timed_effects"):
            status = light.get(key, {}).get("status")
            if isinstance(status, dict):  # effects_v2: {"effect": "...", ...}
                status = status.get("effect")
            if status and status != "no_effect":
                effect = status
                break
        return {
            ATTR_FARBEN: colors,
            ATTR_MODUS: mode,
            ATTR_HELLIGKEIT: round(brightness) if brightness is not None else None,
            ATTR_AN: bool(light.get("on", {}).get("on")),
            ATTR_EFFEKT: effect,
            ATTR_ERREICHBAR: self._reachable(),
            ATTR_SYNC: self._sync_active(),
            ATTR_PUNKTE_MAX: gradient.get("points_capable"),
            ATTR_PIXEL: gradient.get("pixel_count"),
            ATTR_MODI: gradient.get("mode_values", []),
            ATTR_LICHT_ID: self.rid,
        }
