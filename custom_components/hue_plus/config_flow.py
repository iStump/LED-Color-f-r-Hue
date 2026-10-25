"""Einrichtung von LED Color über die Oberfläche."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    HueConnectionError,
    HueError,
    HueLinkButtonNotPressed,
    async_create_app_key,
    async_get_bridge_config,
)
from .const import CONF_APP_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HuePlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Schritt 1: Adresse der Bridge. Schritt 2: Knopf drücken."""

    VERSION = 1

    def __init__(self) -> None:
        """Flow vorbereiten."""
        self._host: str | None = None
        self._bridge_name: str = "Hue Bridge"

    def _suggested_host(self) -> str:
        """Adresse der offiziellen Hue-Integration vorschlagen, falls vorhanden."""
        known = {entry.data.get(CONF_HOST) for entry in self._async_current_entries()}
        for entry in self.hass.config_entries.async_entries("hue"):
            host = entry.data.get(CONF_HOST)
            if host and host not in known:
                return host
        return ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Adresse der Bridge abfragen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            session = async_get_clientsession(self.hass, verify_ssl=False)
            try:
                config = await async_get_bridge_config(session, host)
            except HueConnectionError:
                errors["base"] = "cannot_connect"
            else:
                bridge_id = str(config.get("bridgeid", "")).lower()
                model = str(config.get("modelid", ""))
                if not bridge_id:
                    errors["base"] = "not_hue_bridge"
                elif model == "BSB001":
                    errors["base"] = "bridge_v1"
                else:
                    await self.async_set_unique_id(bridge_id)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                    self._host = host
                    self._bridge_name = config.get("name") or self._bridge_name
                    return await self.async_step_link()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST)
                        or self._suggested_host(),
                    ): str
                }
            ),
            errors=errors,
        )

    async def async_step_link(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Knopf auf der Bridge drücken, dann «Senden»."""
        errors: dict[str, str] = {}
        assert self._host is not None
        if user_input is not None:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            try:
                app_key = await async_create_app_key(session, self._host)
            except HueLinkButtonNotPressed:
                errors["base"] = "link_button"
            except HueConnectionError:
                errors["base"] = "cannot_connect"
            except HueError as err:
                _LOGGER.warning("Koppeln fehlgeschlagen: %s", err)
                errors["base"] = "unknown"
            else:
                data = {CONF_HOST: self._host, CONF_APP_KEY: app_key}
                if self.source == "reauth":
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data=data
                    )
                return self.async_create_entry(
                    title=f"LED Color für Hue ({self._bridge_name})", data=data
                )

        return self.async_show_form(
            step_id="link",
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Schlüssel ungültig – nochmals koppeln."""
        self._host = entry_data[CONF_HOST]
        return await self.async_step_link()
