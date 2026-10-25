"""Empfindlichkeit für Hue-Bewegungsmelder und MotionAware-Bereiche."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HuePlusConfigEntry
from .api import HueClient, HueError
from .const import DOMAIN
from .entity import HuePlusEntity

PARALLEL_UPDATES = 1

# motion = klassischer Bewegungsmelder, convenience_area_motion = MotionAware-Bereich
SENSITIVITY_TYPES = ("motion", "convenience_area_motion")


def has_sensitivity(resource: dict[str, Any]) -> bool:
    """Nur Ressourcen, bei denen die Bridge eine Empfindlichkeit meldet."""
    return resource.get("type") in SENSITIVITY_TYPES and isinstance(
        resource.get("sensitivity"), dict
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HuePlusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Regler anlegen – auch für später hinzugefügte Melder."""
    client = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new(*_: Any) -> None:
        new = [
            HueSensitivityNumber(hass, client, res)
            for res in client.resources.values()
            if has_sensitivity(res) and res["id"] not in known
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
            and has_sensitivity(resource)
        ):
            _add_new()

    entry.async_on_unload(client.subscribe(_on_event))


def area_config(client: HueClient, resource: dict[str, Any]) -> dict[str, Any] | None:
    """MotionAware-Bereich (motion_area_configuration), zu dem die Ressource gehört."""
    rid = resource.get("id")
    for config in client.of_type("motion_area_configuration"):
        if any(s.get("rid") == rid for s in config.get("services", [])) or (
            config.get("id") == resource.get("owner", {}).get("rid")
        ):
            return config
    return None


def area_name(client: HueClient, resource: dict[str, Any]) -> str | None:
    """Name des MotionAware-Bereichs, zu dem diese Ressource gehört."""
    rid = resource.get("id")
    for config in client.of_type("motion_area_configuration"):
        services = config.get("services", [])
        if any(s.get("rid") == rid for s in services) or (
            config.get("id") == resource.get("owner", {}).get("rid")
        ):
            if name := config.get("name"):
                return name
            group = client.get(config.get("group", {}).get("rid"))
            return client.name_of(group)
    return None


class HueSensitivityNumber(HuePlusEntity, NumberEntity):
    """Schieberegler 0 … Maximum, so wie ihn die Bridge vorgibt."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_translation_key = "empfindlichkeit"

    def __init__(
        self, hass: HomeAssistant, client: HueClient, resource: dict[str, Any]
    ) -> None:
        """Regler für einen Melder oder Bereich."""
        super().__init__(client, resource)
        self._attr_unique_id = f"{self.rid}_empfindlichkeit"
        if self.rtype == "convenience_area_motion":
            # beim Raum/der Zone anzeigen, wie der offizielle MotionAware-Schalter
            self._attr_translation_key = "motionaware_empfindlichkeit"
            config = area_config(client, resource) or {}
            group = client.get(config.get("group", {}).get("rid"))
            hue_id = (
                group["id"]
                if group and group.get("type") in ("room", "zone")
                else client.bridge.get("bridge_id")
            )
        else:
            hue_id = resource.get("owner", {}).get("rid")
        self._linked = self.link_to_hue_device(hass, hue_id)
        self._update_from_resource()
        self.set_entity_id("number", self._long_name())

    def _long_name(self) -> str:
        """Ausgeschriebener Name (für die ID und falls kein Hue-Gerät gefunden wird)."""
        res = self.resource
        if self.rtype == "convenience_area_motion":
            name = area_name(self.client, res) or self.client.name_of(res)
            return f"MotionAware {name or 'Bereich'} Empfindlichkeit"
        return f"{self.client.name_of(res) or 'Bewegungsmelder'} Empfindlichkeit"

    @callback
    def _update_from_resource(self) -> None:
        if not self._linked:
            self._attr_name = self._long_name()

    @property
    def native_max_value(self) -> float:
        """Höchste Stufe laut Bridge."""
        return float(self.resource.get("sensitivity", {}).get("sensitivity_max") or 10)

    @property
    def native_value(self) -> float | None:
        """Aktuelle Stufe."""
        value = self.resource.get("sensitivity", {}).get("sensitivity")
        return float(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ob die Änderung schon beim Melder angekommen ist."""
        status = self.resource.get("sensitivity", {}).get("status")
        return {
            "status": {"set": "übernommen", "changing": "wird übertragen"}.get(
                status, status
            ),
            "aktiv": self.resource.get("enabled"),
        }

    async def async_set_native_value(self, value: float) -> None:
        """Neue Stufe an die Bridge schicken."""
        try:
            await self.client.async_update_resource(
                self.rtype, self.rid, {"sensitivity": {"sensitivity": int(value)}}
            )
        except HueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bridge_error",
                translation_placeholders={"error": str(err)},
            ) from err
