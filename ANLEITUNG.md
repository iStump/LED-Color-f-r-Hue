# LED Color für Hue – Anleitung

## Installieren (einmalig)

1. HACS → ⋮ oben rechts → *Benutzerdefinierte Repositories*
   → `https://github.com/iStump/LED-Color-f-r-Hue`, Typ *Integration* → *Hinzufügen*.
2. In HACS «LED Color für Hue» suchen → *Herunterladen* → Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → *Integration hinzufügen* → «LED Color für Hue».
   Die Adresse der Bridge ist vorausgefüllt → *Senden* → Knopf auf der Bridge drücken → *Senden*.

Voraussetzung: eckige Hue Bridge (V2) oder Bridge Pro, offizielle Hue-Integration installiert.

## Updates

HACS zeigt neue Versionen von selbst an: «LED Color für Hue» → *Aktualisieren* → Home Assistant
neu starten → Seite einmal neu laden. Nichts löschen, nichts neu einrichten.

## Die Seite «LED Color» (Seitenleiste)

- **Verläufe:** Lampe oben wählen. Farbpunkt antippen → Farbe in der Scheibe oder Weisston wählen.
  Punkt ziehen → Reihenfolge ändern. Dazu Helligkeit, Verteilung, *Zurück*, *Punkt dazu/weg*,
  *Umdrehen*, *Übertragen*, *Als Favorit*.
- **Gekoppelt mit:** zweite Lampe wählen (z. B. Signe R zur Signe L) – sie macht jede Änderung mit,
  auf Wunsch gespiegelt. Die Kopplung merkt sich jedes Gerät (iPad, iPhone) selbst.
- **Effekte:** Kerze, Kaminfeuer, Funkeln … antippen. Sonnenaufgang/-untergang mit wählbarer Dauer.
  Nochmals antippen oder «Effekt aus» beendet den Effekt.
- **Szenen:** alle Hue-Szenen mit echten Farben. Antippen = einschalten, kleines Symbol = dynamisch.
- **Favoriten:** gespeicherte Verläufe (in Home Assistant, auf allen Geräten gleich) auf Lampen legen.
- **Einstellungen:** Einschaltverhalten und Empfindlichkeit aller Geräte nach Raum.

Die Seite ist deutsch; ist Home Assistant auf einer anderen Sprache eingestellt, erscheint sie englisch.

## Als Karte im Dashboard (z. B. Pop-up am Tablet)

Karte hinzufügen → *Manuell* → zum Beispiel:

```yaml
type: custom:led-color-card
ansicht: verlauf
lampe: sensor.hue_plus_wohnzimmer_signe_l_verlauf
paar: sensor.hue_plus_wohnzimmer_signe_r_verlauf
gespiegelt: true
lampenwahl: false
titel: Signe Wohnzimmer
```

```yaml
type: custom:led-color-card
ansicht: szenen
raum: Wohnzimmer
```

| Einstellung | Bedeutung |
|---|---|
| `ansicht` | `verlauf`, `szenen`, `favoriten` oder `einstellungen` |
| `ansichten` | mehrere Bereiche mit Reitern, z. B. `[verlauf, szenen]` (oder `tabs: true` für alle) |
| `lampe` | Lampe, die beim Öffnen gewählt ist |
| `lampenwahl: false` | Lampen-Auswahl ausblenden |
| `paar` + `gespiegelt` | zweite Lampe macht mit (gilt nur für diese Karte) |
| `raum` | nur die Szenen dieses Raums |
| `titel` | Überschrift der Karte |

Die Karte muss nicht als Ressource eingetragen werden – LED Color für Hue lädt sie selbst.

## Sensoren für eigene Dashboards

`sensor.hue_plus_<lampe>_verlauf` – Zustand: Anzahl Farben (z. B. «3 Farben»).
Attribute: `farben` (Hex-Liste), `modus`, `helligkeit` (%), `an`, `erreichbar`, `sync_aktiv`, `effekt`,
`effekte`, `zeit_effekte`, `form`.

Die Farben werden bewusst nicht in der Datenbank gespeichert (sie liegen nur live vor). So bleibt
die Datenbank klein und das Logbuch ruhig.

## Aktionen (für Automationen)

```yaml
action: hue_plus.set_gradient
target: { entity_id: light.wohnzimmer_signe_l }
data: { farben: ["#2f63ff", "#16b8f0", "#ff8a00"], helligkeit: 80, uebergang: 1 }
```

```yaml
action: hue_plus.copy_gradient
target: { entity_id: light.wohnzimmer_signe_r }
data: { von: light.wohnzimmer_signe_l, gespiegelt: true }
```

```yaml
action: hue_plus.set_effect
target: { entity_id: light.schlafzimmer_centris }
data: { effekt: sunrise, dauer: 1200 }   # Sonnenaufgang über 20 Minuten
```

Effekte: `candle`, `fire`, `prism`, `sparkle`, `opal`, `glisten`, `underwater`, `cosmos`, `sunbeam`,
`enchant`, Zeit-Effekte `sunrise`, `sunset`, beenden mit `aus` (nicht jede Lampe kann alle).

## Wenn etwas nicht klappt

- Protokoll: Einstellungen → System → Protokolle → Suche «hue_plus» → Screenshot an Claude.
- Diagnose: Geräte & Dienste → LED Color für Hue → ⋮ → *Diagnose herunterladen* (enthält keinen Schlüssel).

## Entfernen

Geräte & Dienste → LED Color für Hue → ⋮ → *Löschen*, dann in HACS entfernen und neu starten.
In der Hue App unter *Einstellungen → Apps* «hue_plus» entfernen.
