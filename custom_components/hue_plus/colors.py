"""Farben umrechnen: Hue (xy) <-> Hex (#rrggbb)."""

from __future__ import annotations

from typing import Any

from homeassistant.util import color as color_util


def gamut_of(light: dict[str, Any]) -> color_util.GamutType | None:
    """Farbraum der Lampe (jede Hue-Lampe kennt ihr eigenes Dreieck)."""
    gamut = light.get("color", {}).get("gamut")
    try:
        return color_util.GamutType(
            color_util.XYPoint(gamut["red"]["x"], gamut["red"]["y"]),
            color_util.XYPoint(gamut["green"]["x"], gamut["green"]["y"]),
            color_util.XYPoint(gamut["blue"]["x"], gamut["blue"]["y"]),
        )
    except (KeyError, TypeError):
        return None


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """(47, 99, 255) -> '#2f63ff'."""
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(c))) for c in rgb))


def xy_to_hex(xy: dict[str, float], gamut: color_util.GamutType | None) -> str:
    """Hue-Farbpunkt in Hex umrechnen (volle Leuchtkraft, ohne Helligkeit)."""
    rgb = color_util.color_xy_to_RGB(float(xy["x"]), float(xy["y"]), gamut)
    return rgb_to_hex(rgb)


def mirek_to_hex(mirek: int) -> str:
    """Weisston (Farbtemperatur) in Hex umrechnen."""
    kelvin = color_util.color_temperature_mired_to_kelvin(mirek)
    r, g, b = color_util.color_temperature_to_rgb(kelvin)
    return rgb_to_hex((round(r), round(g), round(b)))


def parse_color(value: Any) -> tuple[int, int, int]:
    """'#2f63ff', '2f63ff', 'red', [47, 99, 255] oder '47,99,255' -> RGB."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(int(c) for c in value)  # type: ignore[return-value]
    text = str(value).strip().lower()
    hex_part = text.removeprefix("#")
    if len(hex_part) == 3 and all(c in "0123456789abcdef" for c in hex_part):
        hex_part = "".join(c * 2 for c in hex_part)
    if len(hex_part) == 6 and all(c in "0123456789abcdef" for c in hex_part):
        return (int(hex_part[0:2], 16), int(hex_part[2:4], 16), int(hex_part[4:6], 16))
    if text.count(",") == 2:
        parts = [int(p.strip()) for p in text.split(",")]
        if all(0 <= p <= 255 for p in parts):
            return (parts[0], parts[1], parts[2])
    # Farbnamen wie «red», «orange», «deepskyblue»
    return color_util.color_name_to_rgb(text)


def rgb_to_xy(
    rgb: tuple[int, int, int], gamut: color_util.GamutType | None
) -> dict[str, float]:
    """RGB in Hue-xy umrechnen (innerhalb des Farbraums der Lampe)."""
    x, y = color_util.color_RGB_to_xy(*rgb, gamut)
    return {"x": round(x, 4), "y": round(y, 4)}


def light_colors(light: dict[str, Any]) -> tuple[list[str], str]:
    """Farben einer Lampe als Hex-Liste plus Modus.

    Hat die Lampe einen Verlauf: alle Punkte in der Reihenfolge der Bridge.
    Sonst: eine einzige Farbe (bzw. der Weisston) mit Modus «einfarbig».
    """
    gamut = gamut_of(light)
    gradient = light.get("gradient") or {}
    points = gradient.get("points") or []
    colors = [
        xy_to_hex(p["color"]["xy"], gamut)
        for p in points
        if isinstance(p, dict) and p.get("color", {}).get("xy")
    ]
    if colors:
        return colors, str(gradient.get("mode") or "interpolated_palette")

    ct = light.get("color_temperature") or {}
    if ct.get("mirek_valid") and ct.get("mirek"):
        return [mirek_to_hex(int(ct["mirek"]))], "einfarbig"
    xy = light.get("color", {}).get("xy")
    if xy:
        return [xy_to_hex(xy, gamut)], "einfarbig"
    return [], "einfarbig"
