"""Diagnose-Download (Einstellungen > Geräte & Dienste > LED Color > ⋮ > Diagnose herunterladen).

Enthält die Rohdaten der Bridge zu Lampen mit Verlauf, Bewegungsmeldern,
MotionAware-Bereichen und Automationen – aber KEINEN Schlüssel.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import HuePlusConfigEntry
from .const import CONF_APP_KEY

TO_REDACT = {CONF_APP_KEY, "mac_address", "serial_number", "username", "clientkey"}

INTERESTING_TYPES = {
    "bridge",
    "light",
    "motion",
    "convenience_area_motion",
    "security_area_motion",
    "motion_area_configuration",
    "behavior_instance",
    "entertainment_configuration",
    "smart_scene",
    "zigbee_connectivity",
    "device",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HuePlusConfigEntry
) -> dict[str, Any]:
    """Rohdaten für die Fehlersuche."""
    client = entry.runtime_data
    by_type: dict[str, int] = {}
    for res in client.resources.values():
        by_type[res.get("type", "?")] = by_type.get(res.get("type", "?"), 0) + 1

    devices = {
        res["id"]: {
            "name": res.get("metadata", {}).get("name"),
            "model": res.get("product_data", {}).get("product_name"),
            "model_id": res.get("product_data", {}).get("model_id"),
            "software": res.get("product_data", {}).get("software_version"),
        }
        for res in client.of_type("device")
    }

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "connected": client.connected,
        "resource_count_by_type": dict(sorted(by_type.items())),
        "devices": devices,
        "resources": async_redact_data(
            [
                res
                for res in client.resources.values()
                if res.get("type") in INTERESTING_TYPES
            ],
            TO_REDACT,
        ),
    }
