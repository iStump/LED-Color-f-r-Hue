"""Aktionen hue_plus.set_gradient, hue_plus.copy_gradient und hue_plus.set_effect."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

try:  # neuere HA-Versionen
    from homeassistant.helpers.target import (
        TargetSelection,
    )
    from homeassistant.helpers.target import (
        async_extract_referenced_entity_ids as _extract_new,
    )

    def _referenced(hass: HomeAssistant, call: ServiceCall):
        return _extract_new(hass, TargetSelection(call.data))

except ImportError:  # ältere HA-Versionen
    from homeassistant.helpers.service import (
        async_extract_referenced_entity_ids as _extract_old,
    )

    def _referenced(hass: HomeAssistant, call: ServiceCall):
        return _extract_old(hass, call)

from .api import HueError
from .colors import gamut_of, parse_color, rgb_to_xy
from .const import (
    DOMAIN,
    GRADIENT_MODES,
    SERVICE_COPY_GRADIENT,
    SERVICE_SET_EFFECT,
    SERVICE_SET_GRADIENT,
)

if TYPE_CHECKING:
    from .api import HueClient

ATTR_FARBEN = "farben"
ATTR_MODUS = "modus"
ATTR_HELLIGKEIT = "helligkeit"
ATTR_UEBERGANG = "uebergang"
ATTR_VON = "von"
ATTR_GESPIEGELT = "gespiegelt"
ATTR_HELLIGKEIT_MIT = "helligkeit_uebernehmen"
ATTR_EFFEKT = "effekt"
ATTR_DAUER = "dauer"
ATTR_TEMPO = "tempo"

SET_GRADIENT_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Required(ATTR_FARBEN): vol.All(cv.ensure_list, [vol.Any(str, list)]),
        vol.Optional(ATTR_MODUS): vol.In(GRADIENT_MODES),
        vol.Optional(ATTR_HELLIGKEIT): vol.All(vol.Coerce(float), vol.Range(1, 100)),
        vol.Optional(ATTR_UEBERGANG): vol.All(vol.Coerce(float), vol.Range(0, 3600)),
    }
)

COPY_GRADIENT_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Required(ATTR_VON): cv.entity_id,
        vol.Optional(ATTR_GESPIEGELT, default=False): cv.boolean,
        vol.Optional(ATTR_HELLIGKEIT_MIT, default=True): cv.boolean,
        vol.Optional(ATTR_UEBERGANG): vol.All(vol.Coerce(float), vol.Range(0, 3600)),
    }
)

SET_EFFECT_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Required(ATTR_EFFEKT): cv.string,
        vol.Optional(ATTR_DAUER): vol.All(vol.Coerce(float), vol.Range(1, 21600)),
        vol.Optional(ATTR_TEMPO): vol.All(vol.Coerce(float), vol.Range(0, 1)),
    }
)


def build_effect_payload(light: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Befehl für einen Effekt (Kerze, Feuer …) oder Zeit-Effekt (Sonnenaufgang …)."""
    name = light.get("metadata", {}).get("name", light.get("id"))
    effect = str(data[ATTR_EFFEKT]).strip().lower()
    if effect in ("aus", "off", "none", "no_effect", ""):
        payload: dict[str, Any] = {}
        if "effects_v2" in light:
            payload["effects_v2"] = {"action": {"effect": "no_effect"}}
        elif "effects" in light:
            payload["effects"] = {"effect": "no_effect"}
        if "timed_effects" in light:
            payload["timed_effects"] = {"effect": "no_effect"}
        return payload

    timed = light.get("timed_effects") or {}
    if effect in (timed.get("effect_values") or timed.get("status_values") or []):
        payload = {"timed_effects": {"effect": effect}}
        if (dauer := data.get(ATTR_DAUER)) is not None:
            payload["timed_effects"]["duration"] = int(dauer * 1000)
        return payload

    v2 = light.get("effects_v2") or {}
    if effect in ((v2.get("action") or {}).get("effect_values") or []):
        action: dict[str, Any] = {"effect": effect}
        if (tempo := data.get(ATTR_TEMPO)) is not None:
            action["parameters"] = {"speed": float(tempo)}
        return {"on": {"on": True}, "effects_v2": {"action": action}}

    v1 = light.get("effects") or {}
    if effect in (v1.get("effect_values") or v1.get("status_values") or []):
        return {"on": {"on": True}, "effects": {"effect": effect}}

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="effect_not_supported",
        translation_placeholders={"name": name, "effect": effect},
    )


def _find_light(hass: HomeAssistant, entity_id: str) -> tuple[HueClient, str] | None:
    """Zu einer Entität (Hue-Plus-Verlauf ODER offizielle Hue-Lampe) die Lampe finden."""
    entry = er.async_get(hass).async_get(entity_id)
    if entry is None or entry.unique_id is None:
        return None
    if entry.platform == DOMAIN and entry.unique_id.endswith("_verlauf"):
        rid = entry.unique_id.removesuffix("_verlauf")
    elif entry.platform == "hue" and entry.domain == "light":
        rid = entry.unique_id  # die offizielle Integration nutzt die Lampen-ID
    else:
        return None
    for config_entry in hass.config_entries.async_entries(DOMAIN):
        if config_entry.state is not ConfigEntryState.LOADED:
            continue
        client: HueClient = config_entry.runtime_data
        resource = client.get(rid)
        if resource and resource.get("type") == "light":
            return client, rid
    return None


def _build_payload(light: dict[str, Any], call: ServiceCall) -> dict[str, Any]:
    """Befehl für die Bridge zusammenstellen."""
    gamut = gamut_of(light)
    name = light.get("metadata", {}).get("name", light["id"])
    try:
        rgbs = [parse_color(c) for c in call.data[ATTR_FARBEN]]
    except (ValueError, TypeError) as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_color",
            translation_placeholders={"error": str(err)},
        ) from err
    if not rgbs:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_colors"
        )

    payload: dict[str, Any] = {"on": {"on": True}}
    gradient = light.get("gradient")
    if len(rgbs) == 1:
        # Eine Farbe: ganz normale Farbe setzen
        payload["color"] = {"xy": rgb_to_xy(rgbs[0], gamut)}
    else:
        if not isinstance(gradient, dict):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_gradient",
                translation_placeholders={"name": name},
            )
        capable = int(gradient.get("points_capable") or 5)
        if len(rgbs) > capable:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="too_many_colors",
                translation_placeholders={
                    "name": name,
                    "max": str(capable),
                    "count": str(len(rgbs)),
                },
            )
        payload["gradient"] = {
            "points": [{"color": {"xy": rgb_to_xy(rgb, gamut)}} for rgb in rgbs]
        }
        if mode := call.data.get(ATTR_MODUS):
            allowed = gradient.get("mode_values") or list(GRADIENT_MODES)
            if mode not in allowed:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="mode_not_supported",
                    translation_placeholders={
                        "name": name,
                        "mode": mode,
                        "allowed": ", ".join(allowed),
                    },
                )
            payload["gradient"]["mode"] = mode

    if (brightness := call.data.get(ATTR_HELLIGKEIT)) is not None:
        payload["dimming"] = {"brightness": float(brightness)}
    if (transition := call.data.get(ATTR_UEBERGANG)) is not None:
        payload["dynamics"] = {"duration": int(transition * 1000)}
    return payload


def _resample(points: list[Any], count: int) -> list[Any]:
    """Punkte gleichmässig auf «count» Stück verteilen (erster und letzter bleiben)."""
    if len(points) <= count:
        return points
    return [points[round(i * (len(points) - 1) / (count - 1))] for i in range(count)]


def build_copy_payload(
    src: dict[str, Any], dst: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Farben von Lampe «src» auf Lampe «dst» übertragen (ohne Umrechnungsverlust)."""
    points = [
        p["color"]["xy"]
        for p in (src.get("gradient") or {}).get("points") or []
        if p.get("color", {}).get("xy")
    ]
    if data.get(ATTR_GESPIEGELT):
        points = points[::-1]

    payload: dict[str, Any] = {"on": {"on": True}}
    dst_gradient = dst.get("gradient")
    if len(points) >= 2 and isinstance(dst_gradient, dict):
        capable = int(dst_gradient.get("points_capable") or 5)
        payload["gradient"] = {
            "points": [{"color": {"xy": xy}} for xy in _resample(points, capable)]
        }
        mode = (src.get("gradient") or {}).get("mode")
        if mode and mode in (dst_gradient.get("mode_values") or []):
            payload["gradient"]["mode"] = mode
    elif len(points) >= 2 and "color" in dst:
        # Ziel kann keinen Verlauf: Mischfarbe aller Punkte
        payload["color"] = {
            "xy": {
                "x": round(sum(p["x"] for p in points) / len(points), 4),
                "y": round(sum(p["y"] for p in points) / len(points), 4),
            }
        }
    elif len(points) < 2:
        ct = src.get("color_temperature") or {}
        if ct.get("mirek_valid") and ct.get("mirek") and "color_temperature" in dst:
            payload["color_temperature"] = {"mirek": ct["mirek"]}
        elif src.get("color", {}).get("xy") and "color" in dst:
            payload["color"] = {"xy": src["color"]["xy"]}

    if data.get(ATTR_HELLIGKEIT_MIT, True):
        brightness = src.get("dimming", {}).get("brightness")
        if brightness is not None and "dimming" in dst:
            payload["dimming"] = {"brightness": max(1.0, float(brightness))}
    if (transition := data.get(ATTR_UEBERGANG)) is not None:
        payload["dynamics"] = {"duration": int(transition * 1000)}
    return payload


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Aktionen anmelden."""

    def _targets(call: ServiceCall) -> list[tuple[HueClient, str]]:
        """Alle Ziel-Lampen der Aktion (Lampen, Verlauf-Sensoren, Räume …)."""
        referenced = _referenced(hass, call)
        entity_ids = referenced.referenced | referenced.indirectly_referenced
        targets: list[tuple[HueClient, str]] = []
        for entity_id in sorted(entity_ids):
            if found := _find_light(hass, entity_id):
                if found not in targets:
                    targets.append(found)
            elif entity_id in referenced.referenced:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="unknown_target",
                    translation_placeholders={"entity_id": entity_id},
                )
        if not targets:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_target"
            )
        return targets

    async def _send(client: HueClient, rid: str, payload: dict[str, Any]) -> None:
        try:
            await client.async_update_resource("light", rid, payload)
        except HueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bridge_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def _set_gradient(call: ServiceCall) -> None:
        targets = _targets(call)
        for client, rid in targets:
            await _send(client, rid, _build_payload(client.get(rid) or {}, call))

    async def _copy_gradient(call: ServiceCall) -> None:
        source = _find_light(hass, call.data[ATTR_VON])
        if source is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_target",
                translation_placeholders={"entity_id": call.data[ATTR_VON]},
            )
        src = source[0].get(source[1]) or {}
        for client, rid in _targets(call):
            if (client, rid) == source and not call.data[ATTR_GESPIEGELT]:
                continue  # sich selbst kopieren ändert nichts
            payload = build_copy_payload(src, client.get(rid) or {}, call.data)
            await _send(client, rid, payload)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_GRADIENT, _set_gradient, schema=SET_GRADIENT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_COPY_GRADIENT, _copy_gradient, schema=COPY_GRADIENT_SCHEMA
    )

    async def _set_effect(call: ServiceCall) -> None:
        for client, rid in _targets(call):
            await _send(client, rid, build_effect_payload(client.get(rid) or {}, call.data))

    hass.services.async_register(
        DOMAIN, SERVICE_SET_EFFECT, _set_effect, schema=SET_EFFECT_SCHEMA
    )
