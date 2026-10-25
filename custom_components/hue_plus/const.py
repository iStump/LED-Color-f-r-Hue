"""Konstanten für LED Color (technischer Name: hue_plus)."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "hue_plus"

CONF_APP_KEY: Final = "app_key"

# Name, unter dem sich LED Color auf der Bridge anmeldet (sichtbar in der Hue App
# unter Einstellungen > Apps).
DEVICE_TYPE: Final = "hue_plus#homeassistant"

# Dispatcher-Signal, wenn neue Ressourcen dazukommen oder alles neu geladen wurde
SIGNAL_NEW_RESOURCES: Final = "hue_plus_new_resources_{entry_id}"

# Attributnamen des Verlauf-Sensors – NICHT umbenennen, das 3D-Dashboard liest sie.
ATTR_FARBEN: Final = "farben"
ATTR_MODUS: Final = "modus"
ATTR_HELLIGKEIT: Final = "helligkeit"
ATTR_AN: Final = "an"
ATTR_EFFEKT: Final = "effekt"
ATTR_ERREICHBAR: Final = "erreichbar"
ATTR_SYNC: Final = "sync_aktiv"
ATTR_PUNKTE_MAX: Final = "punkte_max"
ATTR_PIXEL: Final = "pixel"
ATTR_MODI: Final = "modi"
ATTR_LICHT_ID: Final = "licht_id"

MODUS_EINFARBIG: Final = "einfarbig"

GRADIENT_MODES: Final = (
    "interpolated_palette",
    "interpolated_palette_mirrored",
    "random_pixelated",
    "segmented_palette",
)

SERVICE_SET_GRADIENT: Final = "set_gradient"
SERVICE_COPY_GRADIENT: Final = "copy_gradient"
