"""Einschaltverhalten jeder Lampe (was passiert, wenn der Strom zurückkommt)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HuePlusConfigEntry
from .api import HueClient, HueError
from .const import DOMAIN
from .entity import HuePlusEntity

PARALLEL_UPDATES = 1

# Werte der Bridge -> Anzeige (Übersetzungen in translations/*.json)
#   safety         Hue-Standard: geht hell in warmem Weiss an
#   powerfail      genau wie vor dem Stromausfall (war sie aus, bleibt sie aus)
#   last_on_state  geht an, mit der Farbe/Helligkeit vom letzten Mal
#   custom         eigene Einstellung aus der Hue App (nur dort änderbar)
OPTIONS = ["safety", "powerfail", "last_on_state", "custom"]


def has_powerup(resource: dict[str, Any]) -> bool:
    """Nur Lampen, deren Einschaltverhalten die Bridge meldet."""
    return resource.get("type") == "light" and isinstance(resource.get("powerup"), dict)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HuePlusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Für jede Lampe eine Auswahl anlegen – auch für später hinzugefügte."""
    client = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new(*_: Any) -> None:
        new = [
            HuePowerUpSelect(hass, client, light)
            for light in client.of_type("light")
            if has_powerup(light) and light["id"] not in known
        ]
        known.update(e.rid for e in new)
        if new:
            async_add_entities(new)

    _add_new()

    @callback
    def _on_event(event_type: str, resource: dict[str, Any] | None) -> None:
        if event_type in ("add", "refresh"):
            _add_new()

    entry.async_on_unload(client.subscribe(_on_event))


class HuePowerUpSelect(HuePlusEntity, SelectEntity):
    """Auswahl «Einschaltverhalten» einer Lampe."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "einschaltverhalten"
    _attr_options = OPTIONS

    def __init__(
        self, hass: HomeAssistant, client: HueClient, resource: dict[str, Any]
    ) -> None:
        """Auswahl für eine Lampe."""
        super().__init__(client, resource)
        self._attr_unique_id = f"{self.rid}_einschaltverhalten"
        self._linked = self.link_to_hue_device(hass, resource.get("owner", {}).get("rid"))
        self._update_from_resource()
        self.set_entity_id(
            "select", f"{client.name_of(resource) or 'lampe'}_einschaltverhalten"
        )

    @callback
    def _update_from_resource(self) -> None:
        if self._linked:
            return
        name = self.client.name_of(self.resource) or "Hue Lampe"
        self._attr_name = f"{name} Einschaltverhalten"

    @property
    def current_option(self) -> str | None:
        """Aktuelle Einstellung."""
        preset = self.resource.get("powerup", {}).get("preset")
        return preset if preset in OPTIONS else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ob die Lampe die Einstellung schon übernommen hat."""
        return {"uebernommen": self.resource.get("powerup", {}).get("configured")}

    async def async_select_option(self, option: str) -> None:
        """Neue Einstellung an die Bridge schicken."""
        if option == "custom":
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="powerup_custom"
            )
        try:
            await self.client.async_update_resource(
                "light", self.rid, {"powerup": {"preset": option}}
            )
        except HueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bridge_error",
                translation_placeholders={"error": str(err)},
            ) from err
