"""Echte Hue-Szenen aus dem aktuellen Licht bauen (gespeichert in der Bridge).

Eine Hue-Szene gehört immer zu einem Raum oder einer Zone und enthält für jede
Lampe, was sie tun soll (an/aus, Helligkeit, Farbe oder Weisston, Verlauf).
Dazu kommt eine «Palette»: aus ihr macht die Bridge die dynamische Variante.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .colors import light_colors

if TYPE_CHECKING:
    from .api import HueClient

# Die Bridge erlaubt für Szenennamen höchstens 32 Zeichen.
NAME_MAX = 32
# Mehr als 9 Farben nimmt die Hue App für eine Palette nicht.
PALETTE_MAX = 9


def group_light_ids(client: HueClient, group: dict[str, Any]) -> list[str]:
    """Alle Lampen eines Raums (über die Geräte) oder einer Zone (direkt)."""
    ids: list[str] = []
    for child in group.get("children") or []:
        rid, rtype = child.get("rid"), child.get("rtype")
        if rtype == "light":
            ids.append(rid)
        elif rtype == "device":
            device = client.get(rid) or {}
            ids += [
                s["rid"] for s in device.get("services") or [] if s.get("rtype") == "light"
            ]
    # nur Lampen, die die Bridge wirklich kennt, ohne Doppelte
    return [rid for i, rid in enumerate(ids) if client.get(rid) and rid not in ids[:i]]


def _reachable(client: HueClient, light: dict[str, Any]) -> bool | None:
    owner = (light.get("owner") or {}).get("rid")
    for item in client.of_type("zigbee_connectivity"):
        if (item.get("owner") or {}).get("rid") == owner:
            return item.get("status") == "connected"
    return None


def light_preview(client: HueClient, light: dict[str, Any]) -> dict[str, Any]:
    """So sieht eine Lampe jetzt gerade aus (für die Vorschau auf der Seite)."""
    on = bool((light.get("on") or {}).get("on"))
    colors, mode = light_colors(light)
    return {
        "licht_id": light["id"],
        "name": client.name_of(light) or "Lampe",
        "an": on,
        "farben": colors if on else [],
        "modus": mode,
        "helligkeit": (light.get("dimming") or {}).get("brightness"),
        "erreichbar": _reachable(client, light),
    }


def all_groups(client: HueClient) -> list[dict[str, Any]]:
    """Räume und Zonen mit ihren Lampen – Räume zuerst, dann Zonen, je nach Name."""
    result = []
    for rtype in ("room", "zone"):
        for group in client.of_type(rtype):
            lights = [client.get(rid) for rid in group_light_ids(client, group)]
            previews = sorted(
                (light_preview(client, light) for light in lights if light),
                key=lambda p: p["name"].lower(),
            )
            if not previews:
                continue
            result.append(
                {
                    "id": group["id"],
                    "name": client.name_of(group) or "Raum",
                    "typ": rtype,
                    "lichter": previews,
                }
            )
    return sorted(result, key=lambda g: (g["typ"] != "room", g["name"].lower()))


def light_action(light: dict[str, Any]) -> dict[str, Any]:
    """Was die Szene für diese Lampe speichern soll – genau der Zustand von jetzt."""
    on = bool((light.get("on") or {}).get("on"))
    action: dict[str, Any] = {"on": {"on": on}}
    if not on:
        return action
    if (bri := (light.get("dimming") or {}).get("brightness")) is not None:
        action["dimming"] = {"brightness": max(1.0, float(bri))}

    gradient = light.get("gradient") or {}
    points = [
        {"color": {"xy": dict(p["color"]["xy"])}}
        for p in gradient.get("points") or []
        if isinstance(p, dict) and (p.get("color") or {}).get("xy")
    ]
    if len(points) >= 2:
        action["gradient"] = {"points": points}
        if gradient.get("mode"):
            action["gradient"]["mode"] = gradient["mode"]
        return action

    ct = light.get("color_temperature") or {}
    if ct.get("mirek_valid") and ct.get("mirek"):
        action["color_temperature"] = {"mirek": int(ct["mirek"])}
    elif xy := (light.get("color") or {}).get("xy"):
        action["color"] = {"xy": dict(xy)}
    return action


def build_actions(client: HueClient, light_ids: list[str]) -> list[dict[str, Any]]:
    """Aktionen für alle Lampen eines Raums."""
    return [
        {"target": {"rid": rid, "rtype": "light"}, "action": light_action(client.get(rid) or {})}
        for rid in light_ids
        if client.get(rid)
    ]


def build_palette(client: HueClient, actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Palette für «dynamisch»: die Farben aller eingeschalteten Lampen.

    Ohne Farben (nur Weisstöne) gibt es Weisstöne als Palette; ist alles aus, keine.
    """
    colors: list[dict[str, Any]] = []
    temps: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    bris: list[float] = []
    for item in actions:
        action = item["action"]
        if not action["on"]["on"]:
            continue
        bri = (action.get("dimming") or {}).get("brightness", 100.0)
        bris.append(bri)
        xys = [p["color"]["xy"] for p in (action.get("gradient") or {}).get("points", [])]
        if xy := (action.get("color") or {}).get("xy"):
            xys.append(xy)
        for xy in xys:
            key = (round(xy["x"], 3), round(xy["y"], 3))
            if key not in seen:
                seen.add(key)
                colors.append({"color": {"xy": dict(xy)}, "dimming": {"brightness": bri}})
        if mirek := (action.get("color_temperature") or {}).get("mirek"):
            if all(t["color_temperature"]["mirek"] != mirek for t in temps):
                temps.append({"color_temperature": {"mirek": mirek}, "dimming": {"brightness": bri}})
    if not colors and not temps:
        return None
    palette: dict[str, Any] = {
        "color": colors[:PALETTE_MAX],
        "dimming": [],
        "color_temperature": [] if colors else temps[:1],
        "effects": [],
    }
    if not colors and bris:
        palette["dimming"] = [{"brightness": max(bris)}]
    return palette

