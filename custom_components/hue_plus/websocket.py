"""Befehle für die Seite «LED Color»: Szenen (live, anlegen, ändern), Favoriten."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .api import HueError
from .colors import gamut_of, mirek_to_hex, xy_to_hex
from .const import DOMAIN, GRADIENT_MODES, MODUS_EINFARBIG
from .scenes import NAME_MAX, all_groups, build_actions, build_palette, group_light_ids

if TYPE_CHECKING:
    from .api import HueClient

_LOGGER = logging.getLogger(__name__)

STORE_KEY = f"{DOMAIN}.favoriten"
STORE_VERSION = 1
_DATA_STORE = f"{DOMAIN}_favoriten_store"
_HEX = vol.Match(r"^#[0-9a-fA-F]{6}$")


# --------------------------------------------------------------------- Hilfen


def _clients(hass: HomeAssistant) -> list[HueClient]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _action_colors(action: dict[str, Any], gamut: Any) -> list[str]:
    """Farben, die eine Szene für eine Lampe setzt."""
    points = (action.get("gradient") or {}).get("points") or []
    colors = [
        xy_to_hex(p["color"]["xy"], gamut)
        for p in points
        if p.get("color", {}).get("xy")
    ]
    if colors:
        return colors
    if xy := (action.get("color") or {}).get("xy"):
        return [xy_to_hex(xy, gamut)]
    if mirek := (action.get("color_temperature") or {}).get("mirek"):
        return [mirek_to_hex(int(mirek))]
    return []


def scene_info(client: HueClient, scene: dict[str, Any]) -> dict[str, Any]:
    """Eine Hue-Szene so aufbereiten, dass die Seite sie zeichnen kann."""
    group = client.get(scene.get("group", {}).get("rid")) or {}
    lights = []
    for item in scene.get("actions") or []:
        rid = item.get("target", {}).get("rid")
        light = client.get(rid) or {}
        action = item.get("action") or {}
        on = (action.get("on") or {}).get("on", True)
        lights.append(
            {
                "licht_id": rid,
                "name": client.name_of(light) or "Lampe",
                "an": bool(on),
                "farben": _action_colors(action, gamut_of(light)) if on else [],
                "helligkeit": (action.get("dimming") or {}).get("brightness"),
            }
        )
    palette = scene.get("palette") or {}
    palette_colors = [
        xy_to_hex(c["color"]["xy"], None)
        for c in palette.get("color") or []
        if c.get("color", {}).get("xy")
    ] + [
        mirek_to_hex(int(c["color_temperature"]["mirek"]))
        for c in palette.get("color_temperature") or []
        if (c.get("color_temperature") or {}).get("mirek")
    ]
    return {
        "id": scene["id"],
        "name": scene.get("metadata", {}).get("name") or "Szene",
        "raum": client.name_of(group) or "Ohne Raum",
        "raum_id": group.get("id"),
        "raum_typ": group.get("type"),
        "status": (scene.get("status") or {}).get("active", "inactive"),
        "dynamisch_moeglich": bool(palette_colors),
        "palette": palette_colors,
        "tempo": scene.get("speed"),
        "lichter": lights,
    }


def all_scenes(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Alle Szenen aller Bridges, nach Raum und Name sortiert."""
    result = [
        scene_info(client, scene)
        for client in _clients(hass)
        for scene in client.of_type("scene")
    ]
    return sorted(result, key=lambda s: (s["raum"].lower(), s["name"].lower()))


def _store(hass: HomeAssistant) -> Store:
    if _DATA_STORE not in hass.data:
        hass.data[_DATA_STORE] = Store(hass, STORE_VERSION, STORE_KEY)
    return hass.data[_DATA_STORE]


async def _load_favorites(hass: HomeAssistant) -> list[dict[str, Any]]:
    data = await _store(hass).async_load() or {}
    return list(data.get("favoriten", []))


# ------------------------------------------------------------------- Befehle


@websocket_api.websocket_command({vol.Required("type"): "hue_plus/scenes"})
@callback
def ws_scenes(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Alle Szenen einmal holen."""
    connection.send_result(msg["id"], all_scenes(hass))


@websocket_api.websocket_command({vol.Required("type"): "hue_plus/scenes/subscribe"})
@callback
def ws_scenes_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Szenen abonnieren: bei jeder Änderung kommt die ganze Liste neu (max. 3× pro Sekunde)."""
    msg_id = msg["id"]
    pending: dict[str, Any] = {"handle": None}

    @callback
    def _send() -> None:
        pending["handle"] = None
        connection.send_message(websocket_api.event_message(msg_id, all_scenes(hass)))

    @callback
    def _on_event(event_type: str, resource: dict[str, Any] | None) -> None:
        if resource is not None and resource.get("type") not in (
            "scene",
            "room",
            "zone",
        ):
            return
        if pending["handle"] is None:
            pending["handle"] = hass.loop.call_later(0.3, _send)

    unsubs = [client.subscribe(_on_event) for client in _clients(hass)]

    @callback
    def _unsubscribe() -> None:
        for unsub in unsubs:
            unsub()
        if pending["handle"] is not None:
            pending["handle"].cancel()

    connection.subscriptions[msg_id] = _unsubscribe
    connection.send_result(msg_id)
    _send()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hue_plus/scene_activate",
        vol.Required("scene_id"): str,
        vol.Optional("dynamisch", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_scene_activate(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Szene einschalten (auf Wunsch mit dynamischen Farben)."""
    for client in _clients(hass):
        if (client.get(msg["scene_id"]) or {}).get("type") == "scene":
            action = "dynamic_palette" if msg["dynamisch"] else "active"
            try:
                await client.async_update_resource(
                    "scene", msg["scene_id"], {"recall": {"action": action}}
                )
            except HueError as err:
                connection.send_error(msg["id"], "bridge_error", str(err))
                return
            connection.send_result(msg["id"])
            return
    connection.send_error(msg["id"], "not_found", "Szene nicht gefunden")


@websocket_api.websocket_command({vol.Required("type"): "hue_plus/groups"})
@callback
def ws_groups(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Räume und Zonen mit ihren Lampen und deren Farben von jetzt."""
    connection.send_result(
        msg["id"], [group for client in _clients(hass) for group in all_groups(client)]
    )


async def _write_scene(
    client: HueClient, scene_id: str | None, payload: dict[str, Any]
) -> str:
    """Szene anlegen oder ändern. Lehnt die Bridge die Palette ab, ohne Palette nochmals."""
    for attempt in (payload, {k: v for k, v in payload.items() if k != "palette"}):
        try:
            if scene_id:
                await client.async_update_resource("scene", scene_id, attempt)
                return scene_id
            return await client.async_create_resource("scene", attempt)
        except HueError:
            if "palette" not in attempt:
                raise
            _LOGGER.debug("Bridge nimmt die Palette nicht – speichere ohne")
    raise HueError("Szene konnte nicht gespeichert werden")  # pragma: no cover


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hue_plus/scene_save",
        vol.Optional("group_id"): str,
        vol.Optional("scene_id"): str,
        vol.Optional("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=NAME_MAX)),
        vol.Optional("licht_uebernehmen", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_scene_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Echte Hue-Szene aus dem Licht von jetzt anlegen – oder eine bestehende ändern.

    Ohne scene_id: neue Szene im Raum/der Zone group_id (gleicher Name dort = ersetzen).
    Mit scene_id: umbenennen (name) und/oder mit dem Licht von jetzt ersetzen.
    """
    scene_id = msg.get("scene_id")
    group_id = msg.get("group_id")
    name = msg.get("name")
    target = scene_id or group_id
    client = next((c for c in _clients(hass) if c.get(target)), None) if target else None
    if client is None:
        connection.send_error(msg["id"], "not_found", "Raum oder Szene nicht gefunden")
        return

    if scene_id:
        scene = client.get(scene_id) or {}
        if scene.get("type") != "scene":
            connection.send_error(msg["id"], "not_found", "Szene nicht gefunden")
            return
        group = client.get((scene.get("group") or {}).get("rid")) or {}
    else:
        group = client.get(group_id) or {}
        if group.get("type") not in ("room", "zone"):
            connection.send_error(msg["id"], "not_found", "Raum nicht gefunden")
            return
        if not name:
            connection.send_error(msg["id"], "invalid_format", "Bitte einen Namen eingeben")
            return
        # gleicher Name im gleichen Raum: diese Szene ersetzen statt eine zweite anlegen
        for other in client.of_type("scene"):
            if (other.get("group") or {}).get("rid") == group_id and (
                (other.get("metadata") or {}).get("name", "").strip().lower() == name.lower()
            ):
                scene_id = other["id"]
                break

    payload: dict[str, Any] = {}
    if not scene_id:
        payload = {
            "type": "scene",
            "metadata": {"name": name},
            "group": {"rid": group["id"], "rtype": group["type"]},
        }
    elif name:
        payload["metadata"] = {"name": name}

    if not scene_id or msg["licht_uebernehmen"]:
        actions = build_actions(client, group_light_ids(client, group))
        if not actions:
            connection.send_error(msg["id"], "no_lights", "In diesem Raum sind keine Lampen")
            return
        payload["actions"] = actions
        if palette := build_palette(client, actions):
            payload["palette"] = palette

    if not payload:
        connection.send_result(msg["id"], {"scene_id": scene_id})
        return
    try:
        new_id = await _write_scene(client, scene_id, payload)
        await client.async_reload_resource("scene", new_id)
    except HueError as err:
        connection.send_error(msg["id"], "bridge_error", str(err))
        return
    connection.send_result(msg["id"], {"scene_id": new_id, "ersetzt": bool(scene_id)})


@websocket_api.websocket_command(
    {vol.Required("type"): "hue_plus/scene_delete", vol.Required("scene_id"): str}
)
@websocket_api.async_response
async def ws_scene_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Hue-Szene aus der Bridge löschen (verschwindet auch in der Hue App)."""
    for client in _clients(hass):
        if (client.get(msg["scene_id"]) or {}).get("type") == "scene":
            try:
                await client.async_delete_resource("scene", msg["scene_id"])
            except HueError as err:
                connection.send_error(msg["id"], "bridge_error", str(err))
                return
            connection.send_result(msg["id"])
            return
    connection.send_error(msg["id"], "not_found", "Szene nicht gefunden")


@websocket_api.websocket_command({vol.Required("type"): "hue_plus/favorites"})
@websocket_api.async_response
async def ws_favorites(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Gespeicherte Lieblings-Verläufe."""
    connection.send_result(msg["id"], await _load_favorites(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hue_plus/favorites/save",
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=40)),
        vol.Required("farben"): vol.All([_HEX], vol.Length(min=1, max=10)),
        vol.Optional("modus", default="interpolated_palette"): vol.In(
            (*GRADIENT_MODES, MODUS_EINFARBIG)
        ),
        vol.Optional("fav_id"): str,
    }
)
@websocket_api.async_response
async def ws_favorites_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Favorit speichern (neu oder überschreiben)."""
    favorites = await _load_favorites(hass)
    fav_id = msg.get("fav_id") or uuid.uuid4().hex[:10]
    entry = {
        "id": fav_id,
        "name": msg["name"].strip(),
        "farben": [c.lower() for c in msg["farben"]],
        "modus": msg["modus"],
        "erstellt": int(time.time()),
    }
    favorites = [f for f in favorites if f.get("id") != fav_id] + [entry]
    await _store(hass).async_save({"favoriten": favorites})
    connection.send_result(msg["id"], entry)


@websocket_api.websocket_command(
    {vol.Required("type"): "hue_plus/favorites/delete", vol.Required("fav_id"): str}
)
@websocket_api.async_response
async def ws_favorites_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Favorit löschen."""
    favorites = [f for f in await _load_favorites(hass) if f.get("id") != msg["fav_id"]]
    await _store(hass).async_save({"favoriten": favorites})
    connection.send_result(msg["id"])


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Alle Befehle anmelden."""
    for command in (
        ws_scenes,
        ws_scenes_subscribe,
        ws_scene_activate,
        ws_groups,
        ws_scene_save,
        ws_scene_delete,
        ws_favorites,
        ws_favorites_save,
        ws_favorites_delete,
    ):
        websocket_api.async_register_command(hass, command)
