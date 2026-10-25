"""Kleiner, eigener Client für die Hue Bridge (CLIP API v2).

Was er macht:
- holt beim Start alle Ressourcen der Bridge (ein einziger Aufruf),
- hält danach eine Live-Verbindung zum Event-Stream der Bridge offen und
  übernimmt jede Änderung sofort in seinen Zwischenspeicher,
- meldet die Änderung an die Entitäten, die sich dafür angemeldet haben.

Es wird nichts regelmässig abgefragt. Bricht die Verbindung ab, verbindet er
neu und lädt einmal alles frisch.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .const import DEVICE_TYPE

_LOGGER = logging.getLogger(__name__)

# Die Bridge erlaubt nur wenige gleichzeitige Anfragen. Die offizielle
# Integration braucht auch welche, darum bleiben wir bescheiden.
MAX_PARALLEL_REQUESTS = 2
REQUEST_TIMEOUT = 15
# Kommt so lange gar nichts über den Event-Stream, verbinden wir neu und laden
# alles frisch. (Ist die offizielle Integration aktiv, kommt etwa jede Minute
# ein Lebenszeichen, das passiert also praktisch nie.)
EVENTSTREAM_IDLE_TIMEOUT = 300

type Listener = Callable[[str, dict[str, Any] | None], None]


class HueError(Exception):
    """Allgemeiner Fehler mit der Bridge."""


class HueConnectionError(HueError):
    """Bridge nicht erreichbar."""


class HueAuthError(HueError):
    """Schlüssel ungültig (z. B. in der Hue App gelöscht)."""


class HueLinkButtonNotPressed(HueError):
    """Beim Koppeln wurde der Knopf auf der Bridge nicht gedrückt."""


def _deep_merge(target: dict[str, Any], update: dict[str, Any]) -> None:
    """Teil-Update aus dem Event-Stream in eine Ressource übernehmen."""
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


async def async_get_bridge_config(
    session: aiohttp.ClientSession, host: str
) -> dict[str, Any]:
    """Öffentliche Grunddaten der Bridge (ohne Schlüssel) holen."""
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(f"https://{host}/api/config", ssl=False) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise HueConnectionError(str(err)) from err


async def async_create_app_key(session: aiohttp.ClientSession, host: str) -> str:
    """Neuen Schlüssel holen – klappt nur kurz nach Druck auf den Bridge-Knopf."""
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.post(
                f"https://{host}/api",
                json={"devicetype": DEVICE_TYPE, "generateclientkey": True},
                ssl=False,
            ) as resp:
                resp.raise_for_status()
                result = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise HueConnectionError(str(err)) from err

    for item in result if isinstance(result, list) else []:
        if "success" in item and item["success"].get("username"):
            return item["success"]["username"]
        if "error" in item:
            if item["error"].get("type") == 101:
                raise HueLinkButtonNotPressed
            raise HueError(item["error"].get("description", "Unbekannter Fehler"))
    raise HueError(f"Unerwartete Antwort der Bridge: {result}")


class HueClient:
    """Verbindung zu einer Hue Bridge über die CLIP API v2."""

    def __init__(self, session: aiohttp.ClientSession, host: str, app_key: str) -> None:
        """Client vorbereiten."""
        self._session = session
        self.host = host
        self._app_key = app_key
        self._semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
        self.resources: dict[str, dict[str, Any]] = {}
        self._listeners: dict[str | None, list[Listener]] = {}
        self._event_task: asyncio.Task | None = None
        self.connected = False
        self._last_event_id: str | None = None
        self._on_auth_failed: Callable[[], None] | None = None

    # ------------------------------------------------------------------ Abfragen

    @property
    def _headers(self) -> dict[str, str]:
        return {"hue-application-key": self._app_key}

    async def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Eine Anfrage an die Bridge schicken (mit kleinem Wiederholen bei «besetzt»)."""
        url = f"https://{self.host}/clip/v2/{path}"
        for attempt in range(1, 5):
            try:
                async with self._semaphore, asyncio.timeout(REQUEST_TIMEOUT):
                    async with self._session.request(
                        method, url, json=payload, headers=self._headers, ssl=False
                    ) as resp:
                        if resp.status in (429, 503):
                            # Bridge ist gerade ausgelastet – kurz warten
                            await asyncio.sleep(0.3 * attempt)
                            continue
                        if resp.status in (401, 403):
                            raise HueAuthError("Schlüssel wird von der Bridge abgelehnt")
                        try:
                            body = await resp.json(content_type=None)
                        except ValueError:
                            body = {}
                        if resp.status >= 400 or body.get("errors"):
                            errors = body.get("errors") or [{"description": resp.reason}]
                            raise HueError(
                                "; ".join(e.get("description", "?") for e in errors)
                            )
                        return body.get("data", [])
            except (aiohttp.ClientError, TimeoutError) as err:
                raise HueConnectionError(str(err)) from err
        raise HueError("Bridge ist überlastet, bitte später nochmals versuchen")

    async def async_refresh(self) -> None:
        """Alle Ressourcen auf einmal laden."""
        data = await self.request("get", "resource")
        self.resources = {item["id"]: item for item in data if "id" in item}
        self._notify("refresh", None)

    async def async_update_resource(
        self, rtype: str, rid: str, payload: dict[str, Any]
    ) -> None:
        """Eine Ressource ändern (z. B. Farbverlauf, Empfindlichkeit)."""
        _LOGGER.debug("PUT %s/%s %s", rtype, rid, payload)
        await self.request("put", f"resource/{rtype}/{rid}", payload)

    # -------------------------------------------------------------- Hilfsfunktionen

    def of_type(self, rtype: str) -> list[dict[str, Any]]:
        """Alle Ressourcen eines Typs (z. B. «light»)."""
        return [r for r in self.resources.values() if r.get("type") == rtype]

    def get(self, rid: str | None) -> dict[str, Any] | None:
        """Ressource nach ID."""
        return self.resources.get(rid) if rid else None

    @property
    def bridge(self) -> dict[str, Any]:
        """Die Bridge-Ressource selbst."""
        bridges = self.of_type("bridge")
        return bridges[0] if bridges else {}

    def name_of(self, resource: dict[str, Any] | None) -> str | None:
        """Anzeigename einer Ressource (aus der Hue App)."""
        if not resource:
            return None
        if name := resource.get("metadata", {}).get("name"):
            return name
        if name := resource.get("name"):
            return name
        owner = resource.get("owner", {}).get("rid")
        if owner and owner != resource.get("id"):
            return self.name_of(self.get(owner))
        return None

    # ----------------------------------------------------------------- Anmelden

    def subscribe(self, listener: Listener, rid: str | None = None) -> Callable[[], None]:
        """Bei Änderungen benachrichtigt werden (rid=None: bei allem)."""
        self._listeners.setdefault(rid, []).append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners.get(rid, []):
                self._listeners[rid].remove(listener)

        return _unsubscribe

    def _notify(self, event_type: str, resource: dict[str, Any] | None) -> None:
        targets = list(self._listeners.get(None, []))
        if resource is not None:
            targets += self._listeners.get(resource.get("id"), [])
        else:
            # Bei «refresh»/«verbunden» sollen sich alle neu zeichnen
            for rid, listeners in self._listeners.items():
                if rid is not None:
                    targets += listeners
        for listener in targets:
            try:
                listener(event_type, resource)
            except Exception:
                _LOGGER.exception("Fehler beim Verarbeiten eines Hue-Ereignisses")

    # ------------------------------------------------------------- Event-Stream

    def start(
        self,
        create_task: Callable[..., asyncio.Task],
        on_auth_failed: Callable[[], None] | None = None,
    ) -> None:
        """Live-Verbindung starten (läuft im Hintergrund)."""
        self._on_auth_failed = on_auth_failed
        self._event_task = create_task(self._event_loop(), "hue_plus_eventstream")

    async def stop(self) -> None:
        """Live-Verbindung beenden."""
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
            self._event_task = None
        self.connected = False

    async def _event_loop(self) -> None:
        attempt = 0
        first = True
        while True:
            try:
                if not first:
                    # nach einem Unterbruch alles frisch laden, damit nichts fehlt
                    await self.async_refresh()
                first = False
                await self._read_stream()
                attempt = 0
            except asyncio.CancelledError:
                raise
            except HueAuthError:
                _LOGGER.error(
                    "Die Hue Bridge lehnt den Schlüssel von LED Color ab. "
                    "Bitte LED Color neu einrichten"
                )
                self._set_connected(False)
                if self._on_auth_failed:
                    self._on_auth_failed()
                return
            except (HueError, aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Event-Stream unterbrochen: %s", err)
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler im Event-Stream")
            self._set_connected(False)
            attempt += 1
            wait = min(2 * attempt, 60)
            if attempt % 10 == 0:
                _LOGGER.warning(
                    "Hue Bridge %s seit %s Versuchen nicht erreichbar", self.host, attempt
                )
            await asyncio.sleep(wait)

    def _set_connected(self, value: bool) -> None:
        if self.connected != value:
            self.connected = value
            self._notify("connection", None)

    async def _read_stream(self) -> None:
        headers = {
            **self._headers,
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        if self._last_event_id:
            headers["Last-Event-ID"] = self._last_event_id
        timeout = aiohttp.ClientTimeout(
            total=None, connect=REQUEST_TIMEOUT, sock_read=EVENTSTREAM_IDLE_TIMEOUT
        )
        async with self._session.get(
            f"https://{self.host}/eventstream/clip/v2",
            headers=headers,
            timeout=timeout,
            ssl=False,
        ) as resp:
            if resp.status in (401, 403):
                raise HueAuthError
            if resp.status >= 400:
                raise HueError(f"Event-Stream: HTTP {resp.status}")
            _LOGGER.debug("Event-Stream verbunden")
            self._set_connected(True)
            async for raw in resp.content:
                self._handle_line(raw)
        raise HueConnectionError("Event-Stream wurde von der Bridge geschlossen")

    def _handle_line(self, raw: bytes) -> None:
        line = raw.decode(errors="ignore").strip()
        if not line or line.startswith(":") or ":" not in line:
            return
        key, value = line.split(":", 1)
        value = value.strip()
        if key == "id":
            self._last_event_id = value
            return
        if key != "data":
            return
        try:
            containers = json.loads(value)
        except ValueError:
            _LOGGER.debug("Unlesbares Ereignis: %s", value[:200])
            return
        for container in containers if isinstance(containers, list) else []:
            event_type = container.get("type")
            for item in container.get("data", []):
                self._apply(event_type, item)

    def _apply(self, event_type: str | None, item: dict[str, Any]) -> None:
        rid = item.get("id")
        if not rid:
            return
        if event_type == "update":
            if rid not in self.resources:
                return  # kennen wir (noch) nicht – kommt beim nächsten Neuladen
            _deep_merge(self.resources[rid], item)
            self._notify("update", self.resources[rid])
        elif event_type == "add":
            self.resources[rid] = item
            self._notify("add", item)
        elif event_type == "delete":
            removed = self.resources.pop(rid, None) or item
            self._notify("delete", removed)
