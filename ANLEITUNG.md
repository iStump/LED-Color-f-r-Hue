# LED Color für Hue 0.3.0 – Update, Test, GitHub

## A. Update über HACS (1 Minute)

1. HACS öffnen → «LED Color für Hue» → *Aktualisieren* (oder ⋮ → *Erneut herunterladen*).
2. Home Assistant neu starten.
3. Seite einmal neu laden (⌘R bzw. in der App nach unten ziehen). In der Seitenleiste erscheint **LED Color**.

Ohne HACS: Ordner `custom_components/hue_plus` durch den neuen ersetzen (siehe Terminal-Befehl im Chat).

## B. Testen

0. **Seite «LED Color»** in der Seitenleiste öffnen:
   - Verläufe: Signe wählen, einen Farbpunkt antippen, in der Farbscheibe eine Farbe wählen → die Lampe ändert sich.
     Einen Punkt mit dem Finger nach oben ziehen → Reihenfolge ändert sich.
   - Szenen: eine Szene antippen → sie geht an und leuchtet in der Liste.
   - Favoriten: unter Verläufe «Als Favorit» speichern, dann unter Favoriten auf die andere Signe legen.
   - Einstellungen: Einschaltverhalten einer Lampe umstellen, in der Hue App kontrollieren.

1. **Name:** Geräte & Dienste → die Integration heisst jetzt «LED Color für Hue».
2. **Erreichbar:** Entwicklerwerkzeuge → Zustände → `verlauf` → Attribut `erreichbar: true`.
   Test: eine Signe am Stecker ziehen → nach einigen Minuten `erreichbar: false` (so lange braucht die Bridge, bis sie es merkt). Wieder einstecken.
3. **Einschaltverhalten:** Gerät der Lampe (z. B. «Wohnzimmer Signe L») → Bereich *Konfiguration* →
   «Einschaltverhalten» → «Wie vor dem Stromausfall».
   In der Hue App bei derselben Lampe unter den Einstellungen kontrollieren.
4. **Verlauf kopieren:** Entwicklerwerkzeuge → Aktionen → YAML-Modus:
   ```yaml
   action: hue_plus.copy_gradient
   target:
     entity_id: sensor.hue_plus_wohnzimmer_signe_r_verlauf
   data:
     von: sensor.hue_plus_wohnzimmer_signe_l_verlauf
     gespiegelt: true
   ```
   → Signe R zeigt die Farben der Signe L in umgekehrter Reihenfolge.

Bei Fehlern: Einstellungen → System → Protokolle → «hue_plus» → Screenshot an Claude.
Diagnose: Geräte & Dienste → LED Color für Hue → ⋮ → *Diagnose herunterladen* (ohne Schlüssel).

## C. GitHub (einmalig, damit Updates künftig über HACS kommen)

HACS kann nur **öffentliche** Repositories installieren. Im Code steht nichts Geheimes – aber
alle können ihn sehen (und deinen GitHub-Namen).

1. Auf github.com ein Konto anlegen (falls noch keins) und **GitHub Desktop** für den Mac laden
   (desktop.github.com) – damit geht alles per Maus.
2. github.com → oben rechts **+** → *New repository* → Name `led-color-for-hue`, **Public**, nichts ankreuzen →
   *Create repository*.
3. Auf der neuen Seite *uploading an existing file* anklicken und den **Inhalt** des ZIP-Ordners
   hineinziehen (`custom_components`, `hacs.json`, `README.md`, `LICENSE`, `ANLEITUNG.md`) →
   *Commit changes*. (Klappt das Ziehen von Ordnern in Safari nicht: mit GitHub Desktop
   *Clone* → Dateien in den Ordner kopieren → *Commit* → *Push*.)
   Der versteckte Ordner `.github` (automatische Prüfung) kann später dazukommen.
4. Rechts *Releases* → *Create a new release* → Tag `v0.2.2` → *Publish release*.
5. **Claude Bescheid geben:** deinen GitHub-Namen + `led-color-for-hue`. Ich trage dann die Adressen in
   `manifest.json` ein (die HACS verlangt) – und schicke dir die Version 0.2.2.
6. In Home Assistant: HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/iStump/LED-Color-f-r-Hue`,
   Typ *Integration* → *Hinzufügen* → «LED Color für Hue» → *Herunterladen* → HA neu starten.
   HACS überschreibt den Ordner `hue_plus` – nichts löschen, nichts neu einrichten.

Tipp: Verbindest du GitHub in den claude.ai-Einstellungen (Connectors), kann Claude neue Versionen
direkt hochladen – du klickst dann in HACS nur noch auf *Aktualisieren*.

## D. Entfernen

Geräte & Dienste → LED Color für Hue → ⋮ → *Löschen*, Ordner `custom_components/hue_plus` löschen, neu starten.
In der Hue App unter *Einstellungen → Apps* «hue_plus» entfernen.
