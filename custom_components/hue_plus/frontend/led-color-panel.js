/*
 * LED Color für Hue – eigene Seite in der Home-Assistant-Seitenleiste.
 *
 * Vier Bereiche:
 *   Verläufe      – Lampe wählen, Farbpunkte antippen/ziehen, Farbe und Helligkeit wählen
 *   Szenen        – alle Hue-Szenen mit ihren echten Farben, antippen = einschalten
 *   Favoriten     – gespeicherte Verläufe auf beliebige Lampen übertragen
 *   Einstellungen – Einschaltverhalten aller Lampen, nach Raum
 *
 * Kein Internet nötig, keine fremden Bibliotheken. Daten kommen live aus Home Assistant
 * (Sensoren sensor.hue_plus_…_verlauf und die Befehle hue_plus/…).
 */

const VERSION = "0.4.1";

const MODES = {
  interpolated_palette: "Fliessend",
  interpolated_palette_mirrored: "Gespiegelt",
  segmented_palette: "Abschnitte",
  random_pixelated: "Funkeln",
};
const POWERUP = [
  ["safety", "Standard"],
  ["powerfail", "Wie vorher"],
  ["last_on_state", "Letzte Farbe"],
];
// Weisstöne von warm nach kalt (für Farbpunkte)
const WHITES = [
  ["2200 K", "#ff9a3c"],
  ["2700 K", "#ffb06b"],
  ["3000 K", "#ffbe82"],
  ["4000 K", "#ffd8b4"],
  ["5000 K", "#ffebd9"],
  ["6500 K", "#f5f3ff"],
];
const SLOTS = 10; // max. Farben, die weich überblendet werden
const EFFECTS = {
  candle: "Kerze", fire: "Kaminfeuer", prism: "Prisma", sparkle: "Funkeln", opal: "Opal", glisten: "Glitzern",
  underwater: "Unterwasser", cosmos: "Kosmos", sunbeam: "Sonnenstrahl", enchant: "Zauber",
  sunrise: "Sonnenaufgang", sunset: "Sonnenuntergang",
};
const DURATIONS = [1, 5, 10, 20, 30]; // Minuten für Sonnenaufgang/-untergang

// ------------------------------------------------------------------ Sprache
// Deutsch ist die Grundsprache; ist Home Assistant auf einer anderen Sprache, kommt Englisch.
const EN = {
  "für Hue": "for Hue", "Verläufe": "Gradients", "Szenen": "Scenes", "Favoriten": "Favorites", "Einstellungen": "Settings",
  "Farbe": "Color", "Helligkeit": "Brightness", "Verteilung": "Distribution", "Effekte": "Effects", "Dauer": "Duration",
  "{n} Min.": "{n} min", "Gekoppelt mit": "Linked with", "Keine": "None", "Effekt aus": "Effect off",
  "Fliessend": "Smooth", "Gespiegelt": "Mirrored", "Abschnitte": "Segments", "Funkeln": "Sparkle", "einfarbig": "single color",
  "Standard": "Default", "Wie vorher": "As before", "Letzte Farbe": "Last color", "Eigene (Hue App)": "Custom (Hue app)",
  "Punkt {n}: {hex}": "Point {n}: {hex}", "Punkt dazu": "Add point", "Punkt weg": "Remove point", "Umdrehen": "Reverse",
  "Übertragen": "Copy to…", "Als Favorit": "Save favorite", "Zurück": "Undo",
  "ohne Strom": "no power", "aus": "off", "Lampe": "Light", "Farbpunkt": "Color point", "Farbe wählen": "Pick color",
  "Licht ein/aus": "Light on/off",
  "Keine Lampe mit Farbverlauf gefunden. Läuft LED Color für Hue?": "No gradient light found. Is LED Color for Hue running?",
  "Lampe hat keinen Strom": "Light has no power", "Hue Sync steuert gerade diese Lampe": "Hue Sync is controlling this light",
  "Punkt antippen, um die Farbe zu ändern. Ziehen, um die Reihenfolge zu ändern.": "Tap a point to change its color. Drag to reorder.",
  "Punkt antippen, um die Farbe zu ändern.": "Tap a point to change its color.",
  "Gekoppelt: {name} macht mit.": "Linked: {name} follows.", "Gekoppelt: {name} macht gespiegelt mit.": "Linked: {name} follows mirrored.",
  "«{name}» übertragen auf": "Copy «{name}» to", "Gespiegelt (Reihenfolge umgedreht)": "Mirrored (reversed order)",
  "Abbrechen": "Cancel", "Bitte mindestens eine Lampe wählen.": "Please choose at least one light.",
  "Übertragen auf {n} Lampe.": "Copied to {n} light.", "Übertragen auf {n} Lampen.": "Copied to {n} lights.",
  "Als Favorit speichern": "Save as favorite", "Name, z. B. Sonnenuntergang": "Name, e.g. Sunset", "Speichern": "Save",
  "Bitte einen Namen eingeben.": "Please enter a name.", "Gespeichert: {name}": "Saved: {name}",
  "Alle": "All", "Noch keine Szenen geladen. Sind in der Hue App Szenen angelegt?": "No scenes loaded yet. Are there scenes in the Hue app?",
  "{n} Szene": "{n} scene", "{n} Szenen": "{n} scenes", "Läuft dynamisch": "Running dynamically", "Aktiv": "Active",
  "{n} Lampe": "{n} light", "{n} Lampen": "{n} lights", "Dynamisch starten": "Start dynamically",
  "Noch keine Favoriten.<br>Stell unter «Verläufe» einen Verlauf zusammen und tippe auf «Als Favorit».":
    "No favorites yet.<br>Build a gradient under «Gradients» and tap «Save favorite».",
  "Deine Verläufe": "Your gradients", "{n} Farbe": "{n} color", "{n} Farben": "{n} colors",
  "Auf welche Lampen?": "Which lights?", "Löschen": "Delete", "Anwenden": "Apply",
  "Gelöscht: {name}": "Deleted: {name}", "«{name}» angewendet.": "«{name}» applied.",
  "Keine Einstellungen gefunden.": "No settings found.", "Ohne Raum": "No area",
  "Einschaltverhalten": "Power-on behavior",
  "Was eine Lampe macht, wenn der Strom zurückkommt, zum Beispiel nach dem Wandschalter oder einem Stromausfall.":
    "What a light does when power returns, for example after the wall switch or a power cut.",
  "Kerze": "Candle", "Kaminfeuer": "Fireplace", "Prisma": "Prism", "Opal": "Opal", "Glitzern": "Glisten",
  "Unterwasser": "Underwater", "Kosmos": "Cosmos", "Sonnenstrahl": "Sunbeam", "Zauber": "Enchant",
  "Sonnenaufgang": "Sunrise", "Sonnenuntergang": "Sunset",
};
let LANG = "de";
const tr = (s, v = {}) => String((LANG === "en" && EN[s]) || s).replace(/\{(\w+)\}/g, (_, k) => v[k] ?? "");
const plural = (n, one, many) => tr(n === 1 ? one : many, { n });
const modeLabel = (m) => tr(MODES[m] || "einfarbig");
const effectLabel = (e) => tr(EFFECTS[e] || e);
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(`ledcolor.${k}`)) ?? d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(`ledcolor.${k}`, JSON.stringify(v)); } catch (e) { /* privat/gesperrt */ } },
};

// ------------------------------------------------------------------ Farben

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const hexToRgb = (h) => {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(h || "").trim());
  if (!m) return [128, 128, 128];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};
const rgbToHex = (c) => "#" + c.map((v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, "0")).join("");
const hsvToRgb = (h, s, v) => {
  const f = (n) => {
    const k = (n + h / 60) % 6;
    return v - v * s * Math.max(0, Math.min(k, 4 - k, 1));
  };
  return [f(5) * 255, f(3) * 255, f(1) * 255];
};
const rgbToHsv = ([r, g, b]) => {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  let h = 0;
  if (d) h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [(h * 60 + 360) % 360, mx ? d / mx : 0, mx];
};

// Liste für die Anzeige (gespiegelt = hin und zurück)
const displayColors = (farben, modus) => {
  const f = farben && farben.length ? farben : ["#333333"];
  return modus === "interpolated_palette_mirrored" && f.length > 1 ? f.concat([...f].reverse().slice(1)) : f;
};
const stops = (n, hard, startDeg, spanDeg) => {
  const out = [];
  for (let i = 0; i < n; i++) {
    const c = `var(--c${i})`;
    if (hard) {
      const a = (i / n) * spanDeg + startDeg, b = ((i + 1) / n) * spanDeg + startDeg;
      out.push(`${c} ${a}${spanDeg === 100 ? "%" : "deg"} ${b}${spanDeg === 100 ? "%" : "deg"}`);
    } else {
      const p = n === 1 ? 0 : (i / (n - 1)) * spanDeg + startDeg;
      out.push(`${c} ${p}${spanDeg === 100 ? "%" : "deg"}`);
    }
  }
  return out.join(", ");
};
// statischer Verlauf (ohne Variablen) für kleine Vorschauen
const linear = (dir, farben) => {
  const f = farben && farben.length ? farben : ["#333333"];
  return f.length === 1 ? f[0] : `linear-gradient(${dir}, ${f.join(", ")})`;
};

let uid = 0;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Farb-Variablen weich überblendbar machen (einmalig, global)
try {
  for (let i = 0; i < SLOTS; i++) CSS.registerProperty({ name: `--c${i}`, syntax: "<color>", inherits: true, initialValue: "#000000" });
} catch (e) { /* schon angemeldet oder alter Browser – dann ohne Überblenden */ }

// ------------------------------------------------------------------ Styles

const STYLE = `
:host {
  --bg: #000;
  --text: #f3efe8;
  --text-2: rgba(243,239,232,.58);
  --text-3: rgba(243,239,232,.34);
  --surface: rgba(255,255,255,.045);
  --surface-2: rgba(255,255,255,.08);
  --line: rgba(255,255,255,.08);
  --accent: #e9c48a;
  --accent-soft: rgba(233,196,138,.14);
  --spring: cubic-bezier(.34,1.56,.64,1);
  --ease: cubic-bezier(.2,.8,.2,1);
  display: block; min-height: 100vh; background: var(--bg); color: var(--text); container-type: inline-size;
  font-family: ui-rounded, -apple-system, BlinkMacSystemFont, "SF Pro Rounded", "Segoe UI", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased; -webkit-tap-highlight-color: transparent;
}
* { box-sizing: border-box; }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
button:focus-visible, [tabindex]:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
ha-icon { --mdc-icon-size: 20px; }

header { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; gap: 14px;
  padding: 14px 20px 12px; background: linear-gradient(#000 70%, rgba(0,0,0,0)); }
.title { font-size: 22px; font-weight: 650; letter-spacing: -.02em; white-space: nowrap; }
.title small { font-weight: 400; color: var(--text-3); margin-left: 6px; font-size: 15px; letter-spacing: 0; }
.tabs { position: relative; display: flex; margin-left: auto; padding: 4px; border-radius: 999px; background: var(--surface); }
.tabs .pill { position: absolute; top: 4px; bottom: 4px; left: 0; border-radius: 999px; background: var(--surface-2);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.06); transition: transform .45s var(--spring), width .45s var(--spring); }
.tabs button { position: relative; padding: 8px 16px; border-radius: 999px; font-size: 15px; color: var(--text-2); transition: color .2s; }
.tabs button[aria-selected="true"] { color: var(--text); }
main { padding: 4px 20px 40px; max-width: 1400px; margin: 0 auto; }
.view { display: none; }
.view.on { display: block; animation: rise .35s var(--ease); }
@keyframes rise { from { opacity: 0; transform: translateY(6px); } }

h2 { font-size: 17px; font-weight: 650; margin: 26px 0 12px; letter-spacing: -.01em; }
h2 span { font-weight: 400; color: var(--text-3); margin-left: 8px; font-size: 14px; }
.muted { color: var(--text-2); }

/* ---------- Lampen-Auswahl */
.lamps { display: flex; gap: 10px; overflow-x: auto; padding: 2px 2px 12px; scrollbar-width: none; }
.lamps::-webkit-scrollbar { display: none; }
.lamp-chip { flex: 0 0 auto; display: flex; align-items: center; gap: 10px; padding: 9px 14px 9px 10px;
  border-radius: 16px; background: var(--surface); transition: background .2s, transform .3s var(--spring); }
.lamp-chip:active { transform: scale(.96); }
.lamp-chip[aria-pressed="true"] { background: var(--accent-soft); box-shadow: inset 0 0 0 1px rgba(233,196,138,.35); }
.lamp-chip i { width: 8px; height: 28px; border-radius: 4px; flex: 0 0 auto; }
.lamp-chip i.h { width: 30px; height: 8px; }
.lamp-chip .off { opacity: .28; filter: saturate(.3); }
.lamp-chip b { font-weight: 550; font-size: 15px; }
.lamp-chip em { display: block; font-style: normal; font-size: 12px; color: var(--text-3); }

/* ---------- Editor */
.editor { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(300px, .9fr); gap: 22px; align-items: start; }
@container (max-width: 860px) { .editor { grid-template-columns: 1fr; } }
/* breit: Lampe bleibt beim Scrollen der Bedienelemente stehen */
@container (min-width: 861px) { .editor .stage { position: sticky; top: 76px; } :host([card]) .editor .stage { top: 12px; } }
.stage { position: relative; aspect-ratio: 4 / 3.4; border-radius: 28px; overflow: hidden; background: #000;
  box-shadow: inset 0 0 0 1px var(--line); touch-action: none; user-select: none; -webkit-user-select: none;
  transition: --c0 .7s, --c1 .7s, --c2 .7s, --c3 .7s, --c4 .7s, --c5 .7s, --c6 .7s, --c7 .7s, --c8 .7s, --c9 .7s; }
.stage .wall, .stage .glow, .stage .glow2, .stage .floor, .stage .lamp, .stage .tv { position: absolute; transition: opacity .7s var(--ease); }
.stage .floor { left: 50%; bottom: -14%; width: 70%; height: 30%; transform: translateX(-50%); border-radius: 50%;
  filter: blur(42px); background: var(--c0); }
.stage .lamp { border-radius: 999px; box-shadow: 0 0 0 1px rgba(255,255,255,.08); }
.stage .tv { background: #050505; border-radius: 6px; box-shadow: 0 0 0 1px #1d1d1d, 0 20px 50px rgba(0,0,0,.8); }
.stage .hint { position: absolute; left: 20px; right: 76px; top: 18px; text-align: left; font-size: 13px; line-height: 1.4; color: var(--text-3); pointer-events: none; }
.stage .power { position: absolute; top: 14px; right: 14px; width: 44px; height: 44px; border-radius: 50%;
  display: grid; place-items: center; background: rgba(255,255,255,.07); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  transition: background .3s, transform .3s var(--spring), box-shadow .3s; }
.stage .power:active { transform: scale(.9); }
.stage .power.on { background: rgba(233,196,138,.22); box-shadow: 0 0 24px rgba(233,196,138,.35); color: var(--accent); }
.bead { position: absolute; width: 30px; height: 30px; margin: -15px 0 0 -15px; border-radius: 50%;
  border: 2.5px solid rgba(255,255,255,.92); touch-action: none;
  box-shadow: 0 0 0 1px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.5), 0 0 22px var(--bead);
  background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.55), rgba(255,255,255,0) 45%), var(--bead);
  transition: left .42s var(--spring), top .42s var(--spring), transform .3s var(--spring); }
.bead.sel { transform: scale(1.32); border-color: #fff; z-index: 2; }
.bead.drag { transition: transform .2s var(--spring); transform: scale(1.45); z-index: 3; }
.bead span { position: absolute; top: 34px; left: 50%; transform: translateX(-50%); font-size: 11px; color: var(--text-3); pointer-events: none; }

/* ---------- Bedienfeld */
.panel { display: flex; flex-direction: column; gap: 18px; }
.card { background: var(--surface); border-radius: 24px; padding: 18px; }
.card h3 { margin: 0 0 12px; font-size: 15px; font-weight: 600; color: var(--text-2); display: flex; justify-content: space-between; }
.card h3 output { color: var(--text); font-variant-numeric: tabular-nums; }
.picker { display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: center; }
.disc { position: relative; width: 190px; height: 190px; border-radius: 50%; touch-action: none;
  background: radial-gradient(circle closest-side, #fff, rgba(255,255,255,0) 100%),
              conic-gradient(from 90deg, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00);
  box-shadow: 0 0 0 1px rgba(255,255,255,.1), 0 10px 40px rgba(0,0,0,.6); }
@container (max-width: 420px) { .disc { width: 160px; height: 160px; } }
.knob { position: absolute; width: 30px; height: 30px; margin: -15px 0 0 -15px; border-radius: 50%; border: 3px solid #fff;
  box-shadow: 0 2px 10px rgba(0,0,0,.6); pointer-events: none; transition: transform .25s var(--spring); }
.disc.active .knob { transform: scale(1.25); }
.whites { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.whites button { height: 40px; border-radius: 14px; font-size: 11.5px; white-space: nowrap; letter-spacing: -.01em; color: rgba(0,0,0,.6); font-weight: 600;
  transition: transform .3s var(--spring); }
.whites button:active { transform: scale(.94); }
.slider { position: relative; height: 44px; border-radius: 16px; background: rgba(255,255,255,.06); touch-action: none; overflow: hidden; }
.slider .fill { position: absolute; inset: 0 auto 0 0; border-radius: 16px; opacity: .9; }
.slider .grip { position: absolute; top: 8px; bottom: 8px; width: 6px; margin-left: -14px; border-radius: 3px; background: rgba(255,255,255,.9); }
.segs { display: flex; gap: 6px; flex-wrap: wrap; }
.segs button { flex: 1 1 auto; min-width: 0; padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,.05);
  font-size: 14px; color: var(--text-2); transition: background .2s, color .2s, transform .3s var(--spring); }
.segs button:active { transform: scale(.95); }
.segs button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); box-shadow: inset 0 0 0 1px rgba(233,196,138,.3); }
.segs button:disabled { opacity: .35; cursor: default; }
.actions { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
.act { display: flex; align-items: center; gap: 8px; justify-content: center; padding: 12px; border-radius: 16px;
  background: rgba(255,255,255,.05); font-size: 14px; transition: transform .3s var(--spring), background .2s; }
.act:active { transform: scale(.95); }
.act:disabled { opacity: .3; }
.act.primary { background: var(--accent-soft); color: var(--accent); }

/* ---------- Szenen & Favoriten */
.filters { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; }
.filters::-webkit-scrollbar { display: none; }
.filters button { flex: 0 0 auto; padding: 8px 14px; border-radius: 999px; background: var(--surface); color: var(--text-2); font-size: 14px; }
.filters button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 14px; }
.scene { position: relative; text-align: left; border-radius: 24px; background: var(--surface); padding: 12px 12px 14px;
  transition: transform .35s var(--spring), box-shadow .4s; }
.scene:active { transform: scale(.97); }
.scene .swatch { position: relative; height: 86px; border-radius: 16px; overflow: hidden; }
.scene .swatch::after { content: ""; position: absolute; inset: 0; background: inherit; filter: blur(18px); opacity: .55; transform: translateY(10px) scale(.9); z-index: -1; }
.scene b { display: block; margin: 12px 4px 2px; font-size: 16px; font-weight: 600; }
.scene small { display: block; margin: 0 4px; font-size: 13px; color: var(--text-3); }
.scene.active { box-shadow: inset 0 0 0 1.5px rgba(233,196,138,.55), 0 0 40px -12px var(--glow, rgba(233,196,138,.5)); }
.scene.active small { color: var(--accent); }
.scene .dyn { position: absolute; top: 20px; right: 20px; width: 36px; height: 36px; border-radius: 50%;
  display: grid; place-items: center; background: rgba(0,0,0,.45); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.scene .dyn.on { color: var(--accent); }
.fav .swatch { height: 64px; border-radius: 999px; }
.empty { padding: 48px 24px; text-align: center; color: var(--text-2); border-radius: 24px; background: var(--surface); }

/* ---------- Einstellungen */
.room { background: var(--surface); border-radius: 24px; padding: 6px 18px; margin-bottom: 14px; }
.room > h2 { margin: 14px 0 6px; }
.row { display: grid; grid-template-columns: minmax(120px, 1fr) minmax(0, 1.6fr); gap: 14px; align-items: center; padding: 12px 0;
  border-top: 1px solid var(--line); }
.row:first-of-type { border-top: 0; }
@container (max-width: 640px) { .row { grid-template-columns: 1fr; gap: 8px; } }
.row .name { font-size: 15px; }
.row .name small { display: block; color: var(--text-3); font-size: 12px; }

/* ---------- Blatt (unten einfahrend) & Hinweis */
.sheet-back { display: none; position: fixed; inset: 0; z-index: 20; background: rgba(0,0,0,.5); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  opacity: 0; transition: opacity .3s; }
.sheet-back.on { opacity: 1; }
.sheet { position: fixed; z-index: 21; left: 50%; bottom: 0; width: min(560px, 100%); transform: translate(-50%, 105%);
  background: #121212; border-radius: 28px 28px 0 0; padding: 10px 20px calc(24px + env(safe-area-inset-bottom));
  box-shadow: 0 -20px 60px rgba(0,0,0,.6); visibility: hidden; transition: transform .5s var(--spring), visibility .5s; }
.sheet.on { transform: translate(-50%, 0); visibility: visible; }
.sheet .grab { width: 40px; height: 5px; border-radius: 3px; background: rgba(255,255,255,.2); margin: 0 auto 14px; }
.sheet h3 { margin: 0 0 14px; font-size: 19px; }
.sheet input[type=text] { width: 100%; padding: 14px 16px; border-radius: 16px; border: 0; background: rgba(255,255,255,.07);
  color: var(--text); font: inherit; font-size: 16px; outline: none; }
.sheet input[type=text]:focus { box-shadow: inset 0 0 0 1.5px rgba(233,196,138,.5); }
.sheet .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 16px; }
.sheet .chips button { padding: 10px 14px; border-radius: 14px; background: rgba(255,255,255,.06); font-size: 14px; color: var(--text-2); }
.sheet .chips button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); }
.sheet .bar { display: flex; gap: 8px; margin-top: 16px; }
.sheet .bar .act { flex: 1; }
.toggle { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; font-size: 15px; }
.switch { width: 52px; height: 32px; border-radius: 16px; background: rgba(255,255,255,.14); position: relative; transition: background .25s; }
.switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 26px; height: 26px; border-radius: 50%; background: #fff;
  transition: transform .4s var(--spring); }
.switch[aria-checked="true"] { background: var(--accent); }
.switch[aria-checked="true"]::after { transform: translateX(20px); }
.toast { position: fixed; z-index: 30; left: 50%; bottom: 24px; transform: translate(-50%, 140%); max-width: calc(100% - 32px);
  padding: 12px 18px; border-radius: 16px; background: #1c1c1c; box-shadow: 0 10px 30px rgba(0,0,0,.6); font-size: 14px;
  opacity: 0; visibility: hidden; transition: transform .45s var(--spring), opacity .3s, visibility .45s; }
.toast.on { transform: translate(-50%, 0); opacity: 1; visibility: visible; }
@container (max-width: 720px) {
  header { flex-wrap: wrap; padding: 10px 16px 10px; gap: 8px 10px; }
  .tabs { order: 3; width: 100%; margin-left: 0; }
  .tabs button { flex: 1 1 0; padding: 8px 2px; font-size: 14px; }
  main { padding: 4px 16px 40px; }
  .stage .tip { display: none; }
  .picker { grid-template-columns: 1fr; justify-items: center; }
  .whites { width: 100%; }
}
/* ---------- als Karte im Dashboard */
:host([card]) { min-height: 0; border-radius: 20px; overflow: hidden; }
:host([card]) header { position: static; padding: 14px 16px 6px; background: none; }
:host([card]) main { padding: 4px 16px 18px; }
:host([card]) .sheet, :host([card]) .sheet-back, :host([card]) .toast { position: absolute; }
:host([card]) { position: relative; }
.pair-note { font-size: 13px; color: var(--accent); margin-top: 10px; min-height: 1em; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0s !important; animation: none !important; }
}
`;

// ------------------------------------------------------------------ Panel

class LedColorPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "verlauf";
    this._lamp = null;
    this._draft = null; // { points: [{id, color}], modus, helligkeit }
    this._editUntil = 0;
    this._sel = 0;
    this._scenes = [];
    this._room = null;
    this._favs = [];
    this._hist = [];
    this._lastSnap = 0;
    this._dauer = store.get("dauer", 10);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    LANG = String(hass.locale?.language || hass.language || "de").toLowerCase().startsWith("de") ? "de" : "en";
    if (first) this._init();
    if (!this._raf) this._raf = requestAnimationFrame(() => { this._raf = null; this._update(); });
  }
  get hass() { return this._hass; }
  set narrow(v) { this._narrow = v; if (this._menu) { this._menu.narrow = v; this._menu.style.display = v ? "" : "none"; } }
  set panel(p) { this._panelCfg = p; }

  connectedCallback() { if (this._hass && !this._unsubScenes) this._subscribe(); }
  disconnectedCallback() {
    if (this._unsubScenes) { this._unsubScenes.then((u) => u && u()).catch(() => {}); this._unsubScenes = null; }
  }

  // ---------------------------------------------------------- Grundgerüst
  _init() {
    const r = this.shadowRoot, cfg = this._cfg;
    const ALL = ["verlauf", "szenen", "favoriten", "einstellungen"];
    const LABEL = { verlauf: "Verläufe", szenen: "Szenen", favoriten: "Favoriten", einstellungen: "Einstellungen" };
    // Als Karte: nur die gewünschten Bereiche; als Seite: alle
    this._views = cfg ? (cfg.ansichten || (cfg.tabs ? ALL : [cfg.ansicht || "verlauf"])).filter((v) => ALL.includes(v)) : ALL;
    if (!this._views.length) this._views = ["verlauf"];
    this._tab = cfg ? (this._views.includes(cfg.ansicht) ? cfg.ansicht : this._views[0]) : this._tab;
    if (cfg?.lampe) this._lamp = cfg.lampe;
    if (cfg?.raum) this._room = cfg.raum;
    const showTabs = this._views.length > 1;
    const head = cfg
      ? (cfg.titel || showTabs ? `<header>${cfg.titel ? `<div class="title">${esc(cfg.titel)}</div>` : ""}${showTabs ? "<nav class=\"tabs\" role=\"tablist\"><span class=\"pill\"></span>" + this._views.map((v) => `<button role="tab" data-tab="${v}">${tr(LABEL[v])}</button>`).join("") + "</nav>" : ""}</header>` : "")
      : `<header>
        <span class="menu"></span>
        <div class="title">LED Color <small>${tr("für Hue")}</small></div>
        <nav class="tabs" role="tablist"><span class="pill"></span>${ALL.map((v) => `<button role="tab" data-tab="${v}">${tr(LABEL[v])}</button>`).join("")}</nav>
      </header>`;
    if (cfg) this.setAttribute("card", "");
    r.innerHTML = `<style>${STYLE}</style>${head}
      <main>
        <section class="view" data-view="verlauf">
          <div class="lamps"></div>
          <div class="editor">
            <div class="stage" aria-label="${tr("Lampe")}"></div>
            <div class="panel">
              <div class="card">
                <h3>${tr("Farbe")} <output class="hex"></output></h3>
                <div class="picker"><div class="disc" aria-label="${tr("Farbe wählen")}"><div class="knob"></div></div><div class="whites"></div></div>
              </div>
              <div class="card"><h3>${tr("Helligkeit")} <output class="bri"></output></h3><div class="slider bright"><div class="fill"></div><div class="grip"></div></div></div>
              <div class="card"><h3>${tr("Verteilung")}</h3><div class="segs modes"></div></div>
              <div class="actions"></div>
              <div class="card pair"><h3>${tr("Gekoppelt mit")}</h3><div class="segs partners"></div>
                <div class="toggle" style="padding-bottom:0">${tr("Gespiegelt (Reihenfolge umgedreht)")}<button class="switch mirror" role="switch" aria-checked="false"></button></div>
                <div class="pair-note"></div></div>
              <div class="card fx"><h3>${tr("Effekte")}</h3><div class="segs effects"></div>
                <div class="durations" style="margin-top:12px"><div class="muted" style="font-size:13px;margin-bottom:8px">${tr("Dauer")}</div><div class="segs dur"></div></div></div>
            </div>
          </div>
        </section>
        <section class="view" data-view="szenen"><div class="filters" ${cfg?.raum ? 'style="display:none"' : ""}></div><div class="scenes"></div></section>
        <section class="view" data-view="favoriten"><div class="favs"></div></section>
        <section class="view" data-view="einstellungen"><div class="settings"></div></section>
      </main>
      <div class="sheet-back"></div><div class="sheet" role="dialog" aria-modal="true"></div>
      <div class="toast" role="status"></div>`;

    // Menü-Knopf von Home Assistant (öffnet die Seitenleiste auf dem Handy)
    if (customElements.get("ha-menu-button")) {
      this._menu = document.createElement("ha-menu-button");
      this._menu.hass = this._hass;
      this._menu.narrow = this._narrow;
      this._menu.style.display = this._narrow ? "" : "none";
      r.querySelector(".menu").appendChild(this._menu);
    }

    r.querySelector(".tabs")?.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-tab]");
      if (b) this._setTab(b.dataset.tab);
    });
    r.querySelector(".sheet-back").addEventListener("click", () => this._closeSheet());
    WHITES.forEach(([label, hex]) => {
      const b = document.createElement("button");
      b.textContent = label; b.style.background = hex;
      b.addEventListener("click", () => this._setPointColor(hex));
      r.querySelector(".whites").appendChild(b);
    });
    this._bindDisc();
    this._bindSlider(r.querySelector(".slider.bright"), (v) => this._setBrightness(v));
    r.querySelector(".switch.mirror").addEventListener("click", () => {
      const p = this._pairOf(this._lamp);
      if (p) this._setPair(this._lamp, p.partner, !p.mirrored);
    });
    if (cfg?.lampenwahl === false) r.querySelector(".lamps").style.display = "none";
    this._subscribe();
    this._loadFavs();
    this._setTab(this._tab);
    if (!this._onResize) { this._onResize = () => this._movePill(); window.addEventListener("resize", this._onResize); }
  }

  _setTab(tab) {
    this._tab = tab;
    const r = this.shadowRoot;
    r.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
    r.querySelectorAll(".view").forEach((v) => v.classList.toggle("on", v.dataset.view === tab));
    this._movePill();
    this._update();
  }

  _movePill() {
    const r = this.shadowRoot, b = r.querySelector(`.tabs button[data-tab="${this._tab}"]`), pill = r.querySelector(".tabs .pill");
    if (!b || !pill) return;
    pill.style.width = `${b.offsetWidth}px`;
    pill.style.transform = `translateX(${b.offsetLeft}px)`;
  }

  _update() {
    if (!this._hass) return;
    if (this._menu) this._menu.hass = this._hass;
    this._movePill();
    if (!this._views.includes(this._tab)) this._tab = this._views[0];
    if (this._tab === "verlauf") this._renderEditor();
    if (this._tab === "szenen") this._renderScenes();
    if (this._tab === "favoriten") this._renderFavs();
    if (this._tab === "einstellungen") this._renderSettings();
  }

  // ---------------------------------------------------------- Daten
  _lamps() {
    const h = this._hass;
    return Object.values(h.states)
      .filter((s) => s.entity_id.startsWith("sensor.") && s.attributes.licht_id && Array.isArray(s.attributes.farben))
      .map((s) => ({
        id: s.entity_id,
        name: this._deviceName(s.entity_id) || String(s.attributes.friendly_name || s.entity_id).replace(/ Verlauf$/, ""),
        a: s.attributes,
        state: s.state,
        light: this._lightOf(s.entity_id),
      }))
      .sort((x, y) => x.name.localeCompare(y.name, "de"));
  }
  _deviceName(entityId) {
    const e = this._hass.entities?.[entityId];
    const d = e?.device_id && this._hass.devices?.[e.device_id];
    return d ? d.name_by_user || d.name : null;
  }
  _lightOf(entityId) {
    const h = this._hass, e = h.entities?.[entityId];
    if (!e?.device_id) return null;
    const hit = Object.values(h.entities).find((x) => x.device_id === e.device_id && x.entity_id.startsWith("light.") && x.platform === "hue");
    return hit ? hit.entity_id : null;
  }
  _areaName(entityId) {
    const h = this._hass, e = h.entities?.[entityId];
    const areaId = e?.area_id || (e?.device_id && h.devices?.[e.device_id]?.area_id);
    return (areaId && h.areas?.[areaId]?.name) || tr("Ohne Raum");
  }

  _subscribe() {
    const c = this._hass?.connection;
    if (!c || this._unsubScenes) return;
    this._unsubScenes = c.subscribeMessage((scenes) => { this._scenes = scenes || []; if (this._tab === "szenen") this._renderScenes(); },
      { type: "hue_plus/scenes/subscribe" }).catch((e) => { this._unsubScenes = null; console.warn("LED Color: Szenen", e); });
  }
  async _loadFavs() {
    try { this._favs = (await this._hass.callWS({ type: "hue_plus/favorites" })) || []; } catch (e) { this._favs = []; }
    if (this._tab === "favoriten") this._renderFavs();
  }
  async _call(domain, service, data) {
    try { await this._hass.callService(domain, service, data); }
    catch (e) { this._toast(e?.message || String(e)); }
  }
  _toast(text) {
    const t = this.shadowRoot.querySelector(".toast");
    t.textContent = text; t.classList.add("on");
    clearTimeout(this._toastT); this._toastT = setTimeout(() => t.classList.remove("on"), 3200);
  }

  // ---------------------------------------------------------- Editor
  _renderEditor() {
    const r = this.shadowRoot, lamps = this._lamps();
    const stage = r.querySelector(".stage");
    if (!lamps.length) {
      r.querySelector(".lamps").innerHTML = "";
      stage.innerHTML = `<div class="hint" style="top:45%">${tr("Keine Lampe mit Farbverlauf gefunden. Läuft LED Color für Hue?")}</div>`;
      return;
    }
    if (!this._lamp || !lamps.find((l) => l.id === this._lamp)) this._lamp = lamps[0].id;
    const lamp = lamps.find((l) => l.id === this._lamp);

    // Lampen-Chips (nur neu bauen, wenn sich etwas sichtbar geändert hat)
    const sig = lamps.map((l) => `${l.id}|${l.name}|${l.a.an}|${l.a.farben.join()}|${l.id === this._lamp}`).join(";");
    if (sig !== this._chipSig) {
      this._chipSig = sig;
      const box = r.querySelector(".lamps");
      box.innerHTML = lamps.map((l) => {
        const vertical = l.a.form === "stab";
        const off = !l.a.an || l.a.erreichbar === false;
        const state = l.a.erreichbar === false ? tr("ohne Strom") : l.a.an ? `${l.a.helligkeit ?? 0} %` : tr("aus");
        return `<button class="lamp-chip" data-id="${esc(l.id)}" aria-pressed="${l.id === this._lamp}">
          <i class="${vertical ? "" : "h"} ${off ? "off" : ""}" style="background:${linear(vertical ? "to top" : "to right", displayColors(l.a.farben, l.a.modus))}"></i>
          <span><b>${esc(l.name)}</b><em>${state}</em></span></button>`;
      }).join("");
      box.querySelectorAll(".lamp-chip").forEach((b) => b.addEventListener("click", () => {
        if (this._lamp === b.dataset.id) return;
        this._lamp = b.dataset.id; this._draft = null; this._editUntil = 0; this._sel = 0; this._shapeSig = null; this._hist = [];
        this._renderEditor();
      }));
    }

    // Entwurf = Lampe, ausser man bearbeitet gerade (sonst springt es)
    if (!this._draft || Date.now() > this._editUntil) {
      const f = lamp.a.farben.length ? lamp.a.farben : ["#ffffff"];
      const keep = this._draft?.points || [];
      this._draft = {
        points: f.map((c, i) => ({ id: keep[i]?.id ?? ++uid, color: c })),
        modus: lamp.a.modus === "einfarbig" ? "interpolated_palette" : lamp.a.modus,
        helligkeit: lamp.a.helligkeit ?? 100,
      };
      this._sel = clamp(this._sel, 0, this._draft.points.length - 1);
    }
    this._paintStage(lamp);
    this._paintControls(lamp);
  }

  // Wo Punkt i auf der Lampe sitzt (0 = Anfang, 1 = Ende).
  // «Gespiegelt»: Punkt 1 an beiden Enden, der letzte Punkt in der Mitte – Perlen auf der ersten Hälfte.
  _frac(i, n, modus) {
    const f = n === 1 ? 0.5 : i / (n - 1);
    return modus === "interpolated_palette_mirrored" && n > 1 ? f / 2 : f;
  }

  _shape(lamp) { return lamp.a.form === "stab" ? "stab" : lamp.a.form === "tv" ? "tv" : "streifen"; }

  // Position (Prozent) eines Punkts t∈[0,1] auf der Lampe
  _pos(shape, t) {
    if (shape === "stab") return [50, 88 - t * 74];
    if (shape === "streifen") return [9 + t * 82, 50];
    // TV: links hoch, oben quer, rechts runter
    const L = { x: 21, y: 25, w: 58, h: 50 };
    const total = L.h * 2 + L.w, d = t * total;
    if (d <= L.h) return [L.x, L.y + L.h - d];
    if (d <= L.h + L.w) return [L.x + (d - L.h), L.y];
    return [L.x + L.w, L.y + (d - L.h - L.w)];
  }
  _tOf(shape, px, py) {
    if (shape === "stab") return clamp((88 - py) / 74, 0, 1);
    if (shape === "streifen") return clamp((px - 9) / 82, 0, 1);
    let best = 0, bd = 1e9;
    for (let i = 0; i <= 200; i++) {
      const [x, y] = this._pos("tv", i / 200), dd = (x - px) ** 2 + ((y - py) * 0.85) ** 2;
      if (dd < bd) { bd = dd; best = i / 200; }
    }
    return best;
  }

  _paintStage(lamp) {
    const stage = this.shadowRoot.querySelector(".stage");
    const shape = this._shape(lamp), d = this._draft;
    const colors = d.points.map((p) => p.color);
    const disp = displayColors(colors, d.modus).slice(0, SLOTS);
    const hard = d.modus === "segmented_palette";
    const on = lamp.a.an && lamp.a.erreichbar !== false;
    const glow = on ? 0.35 + 0.65 * clamp(d.helligkeit / 100, 0, 1) : 0;
    const shapeSig = `${shape}|${disp.length}|${hard}|${lamp.id}`;

    if (shapeSig !== this._shapeSig) {
      this._shapeSig = shapeSig;
      const n = disp.length;
      let html = "";
      if (shape === "stab") {
        const g = `linear-gradient(to top, ${stops(n, hard, 0, 100)})`;
        html = `<div class="floor"></div>
          <div class="glow" style="left:50%;top:6%;width:46%;height:86%;transform:translateX(-50%);border-radius:50%;filter:blur(46px);background:${g}"></div>
          <div class="glow2" style="left:50%;top:10%;width:14%;height:80%;transform:translateX(-50%);border-radius:40px;filter:blur(14px);background:${g}"></div>
          <div class="lamp" style="left:50%;top:12%;width:2.6%;min-width:12px;height:76%;transform:translateX(-50%);background:${g}"></div>`;
      } else if (shape === "streifen") {
        const g = `linear-gradient(to right, ${stops(n, hard, 0, 100)})`;
        html = `<div class="glow" style="left:4%;top:24%;width:92%;height:52%;border-radius:50%;filter:blur(44px);background:${g}"></div>
          <div class="glow2" style="left:7%;top:44%;width:86%;height:12%;border-radius:40px;filter:blur(12px);background:${g}"></div>
          <div class="lamp" style="left:9%;top:calc(50% - 6px);width:82%;height:12px;background:${g}"></div>`;
      } else {
        const g = `conic-gradient(from 225deg, ${stops(n, hard, 0, 270)}, transparent 270deg 360deg)`;
        html = `<div class="glow" style="left:2%;top:0;width:96%;height:100%;filter:blur(48px);background:${g}"></div>
          <div class="glow2" style="left:14%;top:16%;width:72%;height:68%;filter:blur(14px);background:${g}"></div>
          <div class="lamp" style="left:20%;top:23.5%;width:60%;height:53%;border-radius:8px;background:${g}"></div>
          <div class="tv" style="left:21%;top:25%;width:58%;height:50%"></div>`;
      }
      stage.innerHTML = html + `<div class="beads"></div>
        <button class="power" aria-label="${tr("Licht ein/aus")}"><ha-icon icon="mdi:power"></ha-icon></button>
        <div class="hint"></div>`;
      stage.querySelector(".power").addEventListener("click", () => {
        const l = this._lamps().find((x) => x.id === this._lamp);
        if (l?.light) this._call("light", "toggle", { entity_id: l.light });
      });
      this._beadEls = new Map();
    }

    // Farben als Variablen -> CSS blendet weich über
    disp.forEach((c, i) => stage.style.setProperty(`--c${i}`, c));
    stage.querySelectorAll(".glow, .glow2, .floor").forEach((el) => (el.style.opacity = String(el.classList.contains("floor") ? glow * 0.55 : glow)));
    stage.querySelector(".lamp").style.opacity = on ? "1" : ".22";
    const power = stage.querySelector(".power");
    power.style.display = lamp.light ? "" : "none";
    power.classList.toggle("on", on);
    const hint = stage.querySelector(".hint");
    const warn = lamp.a.erreichbar === false ? tr("Lampe hat keinen Strom") : lamp.a.sync_aktiv ? tr("Hue Sync steuert gerade diese Lampe") : "";
    hint.classList.toggle("tip", !warn); // reine Bedienhilfe – auf dem Handy ausgeblendet
    hint.textContent = warn ||
      tr(d.points.length > 1 ? "Punkt antippen, um die Farbe zu ändern. Ziehen, um die Reihenfolge zu ändern." : "Punkt antippen, um die Farbe zu ändern.");

    // Perlen (Farbpunkte)
    const beads = stage.querySelector(".beads");
    const n = d.points.length, alive = new Set();
    d.points.forEach((p, i) => {
      alive.add(p.id);
      let el = this._beadEls.get(p.id);
      if (!el) {
        el = document.createElement("button");
        el.className = "bead";
        el.setAttribute("aria-label", tr("Farbpunkt"));
        el.innerHTML = "<span></span>";
        this._bindBead(el, p.id);
        beads.appendChild(el);
        this._beadEls.set(p.id, el);
      }
      if (this._drag?.id !== p.id) {
        const [x, y] = this._pos(shape, this._frac(i, n, d.modus));
        el.style.left = `${x}%`; el.style.top = `${y}%`;
      }
      el.style.setProperty("--bead", p.color);
      el.classList.toggle("sel", i === this._sel);
      el.querySelector("span").textContent = String(i + 1);
    });
    for (const [id, el] of this._beadEls) if (!alive.has(id)) { el.remove(); this._beadEls.delete(id); }
  }

  _bindBead(el, id) {
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      const idx = this._draft.points.findIndex((p) => p.id === id);
      this._sel = idx;
      this._drag = { id, x: e.clientX, y: e.clientY, moved: false };
      el.setPointerCapture(e.pointerId);
      this._touch();
      this._repaint();
    });
    el.addEventListener("pointermove", (e) => {
      const dr = this._drag;
      if (!dr || dr.id !== id) return;
      if (!dr.moved && Math.hypot(e.clientX - dr.x, e.clientY - dr.y) < 6) return;
      if (!dr.moved) this._snap(true);
      dr.moved = true;
      el.classList.add("drag");
      const lamp = this._lamps().find((l) => l.id === this._lamp);
      const shape = this._shape(lamp), rect = this.shadowRoot.querySelector(".stage").getBoundingClientRect();
      const px = ((e.clientX - rect.left) / rect.width) * 100, py = ((e.clientY - rect.top) / rect.height) * 100;
      const t = this._tOf(shape, px, py);
      const [x, y] = this._pos(shape, t);
      el.style.left = `${x}%`; el.style.top = `${y}%`;
      const pts = this._draft.points, n = pts.length;
      const span = this._draft.modus === "interpolated_palette_mirrored" ? clamp(t * 2, 0, 1) : t;
      const from = pts.findIndex((p) => p.id === id), to = n === 1 ? 0 : Math.round(span * (n - 1));
      if (to !== from) {
        const [p] = pts.splice(from, 1); pts.splice(to, 0, p);
        this._sel = to;
        this._touch();
        this._repaint();
      }
    });
    const end = () => {
      const dr = this._drag;
      if (!dr || dr.id !== id) return;
      this._drag = null;
      el.classList.remove("drag");
      if (dr.moved) this._apply();
      this._repaint();
    };
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
  }

  _paintControls(lamp) {
    const r = this.shadowRoot, d = this._draft, p = d.points[this._sel] || d.points[0];
    // Farbscheibe
    const [h, s, v] = rgbToHsv(hexToRgb(p.color));
    const disc = r.querySelector(".disc"), knob = r.querySelector(".knob");
    const rad = (h * Math.PI) / 180, R = 50 * Math.min(1, s * (v < 1 ? v : 1));
    knob.style.left = `${50 + Math.cos(rad) * R}%`;
    knob.style.top = `${50 + Math.sin(rad) * R}%`;
    knob.style.background = p.color;
    disc.dataset.ready = "1";
    r.querySelector(".hex").textContent = tr("Punkt {n}: {hex}", { n: this._sel + 1, hex: p.color });
    // Helligkeit
    const bri = Math.round(d.helligkeit);
    r.querySelector(".bri").textContent = `${bri} %`;
    const sl = r.querySelector(".slider.bright");
    sl.querySelector(".fill").style.width = `${bri}%`;
    sl.querySelector(".fill").style.background = linear("to right", displayColors(d.points.map((x) => x.color), d.modus));
    sl.querySelector(".grip").style.left = `${bri}%`;
    // Verteilung
    const modi = (lamp.a.modi && lamp.a.modi.length ? lamp.a.modi : Object.keys(MODES)).filter((m) => MODES[m]);
    const ms = r.querySelector(".modes"), sig = modi.join() + d.modus + d.points.length;
    if (ms.dataset.sig !== sig) {
      ms.dataset.sig = sig;
      ms.innerHTML = Object.keys(MODES).filter((m) => modi.includes(m)).map((m) =>
        `<button data-m="${m}" aria-pressed="${m === d.modus}" ${d.points.length < 2 ? "disabled" : ""}>${modeLabel(m)}</button>`).join("");
      ms.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
        this._snap(true); this._draft.modus = b.dataset.m; this._touch(); this._apply(); this._repaint();
      }));
    }
    // Aktionen
    const max = lamp.a.punkte_max || 5, n = d.points.length;
    const acts = r.querySelector(".actions"), asig = `${n}|${max}|${this._lamps().length}|${this._hist.length > 0}`;
    if (acts.dataset.sig !== asig) {
      acts.dataset.sig = asig;
      acts.innerHTML = `
        <button class="act" data-a="undo" ${this._hist.length ? "" : "disabled"}><ha-icon icon="mdi:undo-variant"></ha-icon>${tr("Zurück")}</button>
        <button class="act" data-a="add" ${n >= max ? "disabled" : ""}><ha-icon icon="mdi:plus-circle-outline"></ha-icon>${tr("Punkt dazu")}</button>
        <button class="act" data-a="del" ${n <= 1 ? "disabled" : ""}><ha-icon icon="mdi:minus-circle-outline"></ha-icon>${tr("Punkt weg")}</button>
        <button class="act" data-a="rev" ${n < 2 ? "disabled" : ""}><ha-icon icon="mdi:swap-horizontal"></ha-icon>${tr("Umdrehen")}</button>
        <button class="act" data-a="copy" ${this._lamps().length < 2 ? "disabled" : ""}><ha-icon icon="mdi:content-copy"></ha-icon>${tr("Übertragen")}</button>
        <button class="act primary" data-a="fav"><ha-icon icon="mdi:heart-outline"></ha-icon>${tr("Als Favorit")}</button>`;
      acts.querySelectorAll(".act").forEach((b) => b.addEventListener("click", () => this._action(b.dataset.a)));
    }
    this._paintPair(lamp);
    this._paintEffects(lamp);
  }

  // ---------- Koppeln (z. B. beide Signe): Partner macht jede Änderung mit
  _pairs() {
    const p = { ...store.get("paare", {}) };
    const c = this._cfg;
    if (c?.lampe && c?.paar) {
      p[c.lampe] = { partner: c.paar, mirrored: !!c.gespiegelt };
      p[c.paar] = { partner: c.lampe, mirrored: !!c.gespiegelt };
    }
    return p;
  }
  _pairOf(id) {
    const p = this._pairs()[id];
    return p && this._hass.states[p.partner] ? p : null;
  }
  _setPair(id, partner, mirrored) {
    const all = store.get("paare", {});
    const old = all[id]?.partner;
    if (old) delete all[old];
    delete all[id];
    if (partner) {
      if (all[partner]?.partner) delete all[all[partner].partner];
      all[id] = { partner, mirrored };
      all[partner] = { partner: id, mirrored };
    }
    store.set("paare", all);
    this._paintPair(this._lamps().find((l) => l.id === this._lamp));
  }
  _paintPair(lamp) {
    const r = this.shadowRoot, box = r.querySelector(".partners");
    const others = this._lamps().filter((l) => l.id !== lamp.id);
    r.querySelector(".card.pair").style.display = others.length ? "" : "none";
    const pair = this._pairOf(lamp.id);
    const sig = lamp.id + others.map((l) => l.id + l.name).join() + JSON.stringify(pair);
    if (box.dataset.sig !== sig) {
      box.dataset.sig = sig;
      box.innerHTML = [`<button data-p="" aria-pressed="${!pair}">${tr("Keine")}</button>`]
        .concat(others.map((l) => `<button data-p="${esc(l.id)}" aria-pressed="${pair?.partner === l.id}">${esc(l.name)}</button>`)).join("");
      box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () =>
        this._setPair(lamp.id, b.dataset.p || null, this._pairOf(lamp.id)?.mirrored ?? true)));
    }
    const sw = r.querySelector(".switch.mirror");
    sw.setAttribute("aria-checked", String(!!pair?.mirrored));
    sw.disabled = !pair;
    sw.parentElement.style.opacity = pair ? "1" : ".4";
    const partner = pair && this._lamps().find((l) => l.id === pair.partner);
    r.querySelector(".pair-note").textContent = partner
      ? tr(pair.mirrored ? "Gekoppelt: {name} macht gespiegelt mit." : "Gekoppelt: {name} macht mit.", { name: partner.name }) : "";
  }

  // ---------- Effekte (Kerze, Kaminfeuer …) und Sonnenaufgang mit Dauer
  _paintEffects(lamp) {
    const r = this.shadowRoot, card = r.querySelector(".card.fx");
    const fx = lamp.a.effekte || [], timed = lamp.a.zeit_effekte || [];
    card.style.display = fx.length || timed.length ? "" : "none";
    const active = lamp.a.effekt || null;
    const box = r.querySelector(".effects"), sig = [lamp.id, ...fx, "|", ...timed, active].join();
    if (box.dataset.sig !== sig) {
      box.dataset.sig = sig;
      box.innerHTML = [...fx, ...timed].map((e) =>
        `<button data-fx="${esc(e)}" aria-pressed="${e === active}">${esc(effectLabel(e))}</button>`).join("") +
        (active ? `<button data-fx="aus">${tr("Effekt aus")}</button>` : "");
      box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
        const e = b.dataset.fx;
        const data = { entity_id: lamp.id, effekt: e === active ? "aus" : e };
        if (timed.includes(e) && e !== active) data.dauer = this._dauer * 60;
        this._call("hue_plus", "set_effect", data);
      }));
    }
    const dur = r.querySelector(".durations");
    dur.style.display = timed.length ? "" : "none";
    const dbox = r.querySelector(".dur"), dsig = String(this._dauer);
    if (dbox.dataset.sig !== dsig) {
      dbox.dataset.sig = dsig;
      dbox.innerHTML = DURATIONS.map((m) => `<button data-d="${m}" aria-pressed="${m === this._dauer}">${tr("{n} Min.", { n: m })}</button>`).join("");
      dbox.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
        this._dauer = Number(b.dataset.d); store.set("dauer", this._dauer);
        const cur = this._lamps().find((l) => l.id === this._lamp);
        if (cur) this._paintEffects(cur);
      }));
    }
  }

  // ---------- Rückgängig: Zustand vor einer Änderung merken (schnelle Folgen zählen als eine)
  _snap(force) {
    const now = Date.now();
    if (!this._draft || (!force && now - this._lastSnap < 700)) { this._lastSnap = now; return; }
    this._lastSnap = now;
    this._hist.push({ sel: this._sel, d: { ...this._draft, points: this._draft.points.map((p) => ({ ...p })) } });
    if (this._hist.length > 40) this._hist.shift();
  }

  _repaint() {
    const lamp = this._lamps().find((l) => l.id === this._lamp);
    if (!lamp) return;
    this._paintStage(lamp);
    this._paintControls(lamp);
  }
  _touch() { this._editUntil = Date.now() + 3000; }

  _action(a) {
    const d = this._draft, lamp = this._lamps().find((l) => l.id === this._lamp);
    if (a === "undo") {
      const last = this._hist.pop();
      if (!last) return;
      this._draft = last.d; this._sel = last.sel;
      this._touch(); this._apply(); this._repaint();
      return;
    }
    if (["add", "del", "rev"].includes(a)) this._snap(true);
    if (a === "add") {
      const i = this._sel, cur = hexToRgb(d.points[i].color);
      // zwischen zwei Punkten: Mischfarbe; am Ende: Farbton ein Stück weiterdrehen
      const mid = d.points[i + 1]
        ? cur.map((v, k) => (v + hexToRgb(d.points[i + 1].color)[k]) / 2)
        : hsvToRgb((rgbToHsv(cur)[0] + 40) % 360, 0.85, 1);
      d.points.splice(i + 1, 0, { id: ++uid, color: rgbToHex(mid) });
      this._sel = i + 1;
    } else if (a === "del") {
      d.points.splice(this._sel, 1);
      this._sel = clamp(this._sel - 1, 0, d.points.length - 1);
    } else if (a === "rev") {
      d.points.reverse();
      this._sel = d.points.length - 1 - this._sel;
    } else if (a === "copy") {
      return this._copySheet(lamp);
    } else if (a === "fav") {
      return this._favSheet();
    }
    this._touch(); this._apply(); this._repaint();
  }

  _setPointColor(hex) {
    const p = this._draft?.points[this._sel];
    if (!p) return;
    this._snap(); p.color = hex; this._touch(); this._apply(); this._repaint();
  }
  _setBrightness(v) {
    if (!this._draft) return;
    this._snap(); this._draft.helligkeit = clamp(Math.round(v), 1, 100); this._touch(); this._apply(); this._repaint();
  }

  _bindDisc() {
    const disc = this.shadowRoot.querySelector(".disc");
    const pick = (e) => {
      const r = disc.getBoundingClientRect();
      const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
      const s = clamp(Math.hypot(dx, dy) / (r.width / 2), 0, 1);
      const h = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
      this._setPointColor(rgbToHex(hsvToRgb(h, s, 1)));
    };
    disc.addEventListener("pointerdown", (e) => { e.preventDefault(); disc.setPointerCapture(e.pointerId); disc.classList.add("active"); pick(e); });
    disc.addEventListener("pointermove", (e) => { if (disc.classList.contains("active")) pick(e); });
    const up = () => disc.classList.remove("active");
    disc.addEventListener("pointerup", up); disc.addEventListener("pointercancel", up);
  }

  _bindSlider(el, onChange, onEnd) {
    const set = (e) => {
      const r = el.getBoundingClientRect();
      onChange(clamp(((e.clientX - r.left) / r.width) * 100, 0, 100));
    };
    el.addEventListener("pointerdown", (e) => { e.preventDefault(); el.setPointerCapture(e.pointerId); el.dataset.down = "1"; set(e); });
    el.addEventListener("pointermove", (e) => { if (el.dataset.down) set(e); });
    const up = (e) => { if (el.dataset.down) { delete el.dataset.down; if (onEnd) onEnd(e); } };
    el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
  }

  // Änderungen gesammelt an die Lampe schicken (max. ca. 4× pro Sekunde)
  _apply() {
    clearTimeout(this._applyT);
    this._applyT = setTimeout(() => {
      const d = this._draft;
      if (!d) return;
      const farben = d.points.map((p) => p.color);
      const data = { entity_id: this._lamp, farben, helligkeit: d.helligkeit, uebergang: 0.4 };
      if (d.points.length > 1) data.modus = d.modus;
      this._call("hue_plus", "set_gradient", data);
      // gekoppelte Lampe macht mit (auf Wunsch gespiegelt)
      const pair = this._pairOf(this._lamp);
      const partner = pair && this._lamps().find((l) => l.id === pair.partner);
      if (partner) {
        let f = pair.mirrored ? [...farben].reverse() : [...farben];
        const max = partner.a.punkte_max || 5;
        if (f.length > max) f = Array.from({ length: max }, (_, i) => f[Math.round((i * (f.length - 1)) / (max - 1))]);
        const pd = { entity_id: partner.id, farben: f, helligkeit: d.helligkeit, uebergang: 0.4 };
        if (f.length > 1 && (!partner.a.modi?.length || partner.a.modi.includes(d.modus))) pd.modus = d.modus;
        this._call("hue_plus", "set_gradient", pd);
      }
    }, 250);
  }

  // ---------------------------------------------------------- Blätter
  _openSheet(html, bind) {
    const r = this.shadowRoot, sh = r.querySelector(".sheet"), back = r.querySelector(".sheet-back");
    sh.innerHTML = `<div class="grab"></div>${html}`;
    back.style.display = "block";
    requestAnimationFrame(() => { back.classList.add("on"); sh.classList.add("on"); });
    bind(sh);
  }
  _closeSheet() {
    const r = this.shadowRoot, sh = r.querySelector(".sheet"), back = r.querySelector(".sheet-back");
    sh.classList.remove("on"); back.classList.remove("on");
    setTimeout(() => { if (!sh.classList.contains("on")) back.style.display = "none"; }, 350);
  }
  _lampChips(selected, exclude) {
    return this._lamps().filter((l) => l.id !== exclude).map((l) =>
      `<button data-id="${esc(l.id)}" aria-pressed="${selected.includes(l.id)}">${esc(l.name)}</button>`).join("");
  }
  _bindChips(sh, selected) {
    sh.querySelectorAll(".chips button").forEach((b) => b.addEventListener("click", () => {
      const i = selected.indexOf(b.dataset.id);
      if (i >= 0) selected.splice(i, 1); else selected.push(b.dataset.id);
      b.setAttribute("aria-pressed", String(i < 0));
    }));
  }
  _bindSwitch(sh) {
    const sw = sh.querySelector(".switch");
    sw?.addEventListener("click", () => sw.setAttribute("aria-checked", String(sw.getAttribute("aria-checked") !== "true")));
    return () => sw?.getAttribute("aria-checked") === "true";
  }

  _copySheet(lamp) {
    const sel = [];
    this._openSheet(`<h3>${tr("«{name}» übertragen auf", { name: esc(lamp.name) })}</h3>
      <div class="chips">${this._lampChips(sel, lamp.id)}</div>
      <div class="toggle">${tr("Gespiegelt (Reihenfolge umgedreht)")}<button class="switch" role="switch" aria-checked="false"></button></div>
      <div class="bar"><button class="act" data-x="cancel">${tr("Abbrechen")}</button><button class="act primary" data-x="go">${tr("Übertragen")}</button></div>`,
    (sh) => {
      this._bindChips(sh, sel);
      const mirrored = this._bindSwitch(sh);
      sh.querySelector('[data-x="cancel"]').addEventListener("click", () => this._closeSheet());
      sh.querySelector('[data-x="go"]').addEventListener("click", () => {
        if (!sel.length) return this._toast(tr("Bitte mindestens eine Lampe wählen."));
        this._call("hue_plus", "copy_gradient", { von: lamp.id, entity_id: sel, gespiegelt: mirrored(), uebergang: 0.6 });
        this._closeSheet();
        this._toast(plural(sel.length, "Übertragen auf {n} Lampe.", "Übertragen auf {n} Lampen."));
      });
    });
  }

  _favSheet() {
    const d = this._draft, farben = d.points.map((p) => p.color);
    this._openSheet(`<h3>${tr("Als Favorit speichern")}</h3>
      <div class="fav"><div class="swatch" style="background:${linear("to right", displayColors(farben, d.modus))};margin-bottom:14px"></div></div>
      <input type="text" maxlength="40" placeholder="${tr("Name, z. B. Sonnenuntergang")}" aria-label="Name">
      <div class="bar"><button class="act" data-x="cancel">${tr("Abbrechen")}</button><button class="act primary" data-x="save">${tr("Speichern")}</button></div>`,
    (sh) => {
      const input = sh.querySelector("input");
      setTimeout(() => input.focus(), 300);
      sh.querySelector('[data-x="cancel"]').addEventListener("click", () => this._closeSheet());
      const save = async () => {
        const name = input.value.trim();
        if (!name) return this._toast(tr("Bitte einen Namen eingeben."));
        try {
          await this._hass.callWS({ type: "hue_plus/favorites/save", name, farben, modus: d.points.length > 1 ? d.modus : "einfarbig" });
          this._closeSheet(); this._toast(tr("Gespeichert: {name}", { name })); this._loadFavs();
        } catch (e) { this._toast(e?.message || String(e)); }
      };
      sh.querySelector('[data-x="save"]').addEventListener("click", save);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
    });
  }

  // ---------------------------------------------------------- Szenen
  _renderScenes() {
    const r = this.shadowRoot, all = this._scenes;
    const rooms = [...new Set(all.map((s) => s.raum))];
    if (this._room && rooms.length && !rooms.includes(this._room) && !this._cfg?.raum) this._room = null;
    const f = r.querySelector(".filters");
    const fsig = rooms.join("|") + this._room;
    if (f.dataset.sig !== fsig) {
      f.dataset.sig = fsig;
      f.innerHTML = [`<button data-r="" aria-pressed="${!this._room}">${tr("Alle")}</button>`]
        .concat(rooms.map((x) => `<button data-r="${esc(x)}" aria-pressed="${x === this._room}">${esc(x)}</button>`)).join("");
      f.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { this._room = b.dataset.r || null; this._renderScenes(); }));
    }
    const box = r.querySelector(".scenes");
    if (!all.length) { box.innerHTML = `<div class="empty" style="margin-top:14px">${tr("Noch keine Szenen geladen. Sind in der Hue App Szenen angelegt?")}</div>`; return; }
    const shown = this._room ? all.filter((s) => s.raum === this._room) : all;
    const groups = {};
    shown.forEach((s) => (groups[s.raum] = groups[s.raum] || []).push(s));
    const sig = JSON.stringify(shown.map((s) => [s.id, s.status, s.name])) + this._room;
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    box.innerHTML = Object.entries(groups).map(([room, list]) => `
      ${this._cfg?.raum ? "" : `<h2>${esc(room)}<span>${plural(list.length, "{n} Szene", "{n} Szenen")}</span></h2>`}
      <div class="grid">${list.map((s) => this._sceneCard(s)).join("")}</div>`).join("");
    box.querySelectorAll(".scene").forEach((card) => {
      card.addEventListener("click", (e) => {
        const dyn = e.target.closest(".dyn");
        this._activate(card.dataset.id, !!dyn);
      });
    });
  }
  _sceneCard(s) {
    let colors = [];
    s.lichter.forEach((l) => { if (l.an) colors.push(...l.farben); });
    colors = colors.filter((c, i) => c !== colors[i - 1]);
    if (s.status === "dynamic_palette" && s.palette.length) colors = s.palette;
    if (!colors.length) colors = ["#1a1a1a"];
    const active = s.status !== "inactive";
    const lit = s.lichter.filter((l) => l.an).length;
    const state = s.status === "dynamic_palette" ? tr("Läuft dynamisch") : s.status === "static" ? tr("Aktiv") : plural(lit, "{n} Lampe", "{n} Lampen");
    return `<button class="scene ${active ? "active" : ""}" data-id="${esc(s.id)}" style="--glow:${colors[0]}">
      <div class="swatch" style="background:${linear("to right", colors)}"></div>
      ${s.dynamisch_moeglich ? `<span class="dyn ${s.status === "dynamic_palette" ? "on" : ""}" title="${tr("Dynamisch starten")}"><ha-icon icon="mdi:motion-play-outline"></ha-icon></span>` : ""}
      <b>${esc(s.name)}</b><small>${state}</small></button>`;
  }
  async _activate(id, dynamisch) {
    try { await this._hass.callWS({ type: "hue_plus/scene_activate", scene_id: id, dynamisch }); }
    catch (e) { this._toast(e?.message || String(e)); }
  }

  // ---------------------------------------------------------- Favoriten
  _renderFavs() {
    const box = this.shadowRoot.querySelector(".favs");
    const sig = JSON.stringify(this._favs);
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    if (!this._favs.length) {
      box.innerHTML = `<div class="empty" style="margin-top:14px">${tr("Noch keine Favoriten.<br>Stell unter «Verläufe» einen Verlauf zusammen und tippe auf «Als Favorit».")}</div>`;
      return;
    }
    const list = [...this._favs].sort((a, b) => (b.erstellt || 0) - (a.erstellt || 0));
    box.innerHTML = `<h2>${tr("Deine Verläufe")}<span>${list.length}</span></h2><div class="grid">${list.map((f) => `
      <button class="scene fav" data-id="${esc(f.id)}">
        <div class="swatch" style="background:${linear("to right", displayColors(f.farben, f.modus))}"></div>
        <b>${esc(f.name)}</b><small>${plural(f.farben.length, "{n} Farbe", "{n} Farben")}, ${modeLabel(f.modus).toLowerCase()}</small>
      </button>`).join("")}</div>`;
    box.querySelectorAll(".fav").forEach((b) => b.addEventListener("click", () => this._favApplySheet(this._favs.find((f) => f.id === b.dataset.id))));
  }
  _favApplySheet(fav) {
    if (!fav) return;
    const sel = this._lamp ? [this._lamp] : [];
    this._openSheet(`<h3>${esc(fav.name)}</h3>
      <div class="fav"><div class="swatch" style="background:${linear("to right", displayColors(fav.farben, fav.modus))};margin-bottom:14px"></div></div>
      <div class="muted" style="font-size:14px;margin-bottom:8px">${tr("Auf welche Lampen?")}</div>
      <div class="chips">${this._lampChips(sel)}</div>
      <div class="toggle">${tr("Gespiegelt (Reihenfolge umgedreht)")}<button class="switch" role="switch" aria-checked="false"></button></div>
      <div class="bar"><button class="act" data-x="del"><ha-icon icon="mdi:trash-can-outline"></ha-icon>${tr("Löschen")}</button><button class="act primary" data-x="go">${tr("Anwenden")}</button></div>`,
    (sh) => {
      this._bindChips(sh, sel);
      const mirrored = this._bindSwitch(sh);
      sh.querySelector('[data-x="del"]').addEventListener("click", async () => {
        try { await this._hass.callWS({ type: "hue_plus/favorites/delete", fav_id: fav.id }); } catch (e) { return this._toast(String(e?.message || e)); }
        this._closeSheet(); this._toast(tr("Gelöscht: {name}", { name: fav.name })); this._loadFavs();
      });
      sh.querySelector('[data-x="go"]').addEventListener("click", () => {
        if (!sel.length) return this._toast(tr("Bitte mindestens eine Lampe wählen."));
        const lamps = this._lamps();
        sel.forEach((id) => {
          const l = lamps.find((x) => x.id === id);
          let f = mirrored() ? [...fav.farben].reverse() : [...fav.farben];
          const max = l?.a.punkte_max || 5;
          if (f.length > max) f = Array.from({ length: max }, (_, i) => f[Math.round((i * (f.length - 1)) / (max - 1))]);
          const data = { entity_id: id, farben: f, uebergang: 0.8 };
          if (f.length > 1 && fav.modus !== "einfarbig" && (!l?.a.modi?.length || l.a.modi.includes(fav.modus))) data.modus = fav.modus;
          this._call("hue_plus", "set_gradient", data);
        });
        this._editUntil = 0;
        this._closeSheet();
        this._toast(tr("«{name}» angewendet.", { name: fav.name }));
      });
    });
  }

  // ---------------------------------------------------------- Einstellungen
  _renderSettings() {
    const h = this._hass, box = this.shadowRoot.querySelector(".settings");
    const ents = Object.values(h.entities || {}).filter((e) => e.platform === "hue_plus" && h.states[e.entity_id]);
    const rows = ents.filter((e) => e.entity_id.startsWith("select."));
    if (!rows.length) { box.innerHTML = `<div class="empty" style="margin-top:14px">${tr("Keine Einstellungen gefunden.")}</div>`; return; }
    const byRoom = {};
    rows.forEach((e) => (byRoom[this._areaName(e.entity_id)] = byRoom[this._areaName(e.entity_id)] || []).push(e));
    const sig = JSON.stringify(rows.map((e) => [e.entity_id, h.states[e.entity_id].state, this._areaName(e.entity_id)]));
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    const label = (e) => {
      const dev = this._deviceName(e.entity_id);
      const fn = String(h.states[e.entity_id].attributes.friendly_name || e.entity_id);
      return dev || fn.replace(/ (Einschaltverhalten|Power-on behavior)$/, "");
    };
    const none = tr("Ohne Raum");
    const rooms = Object.keys(byRoom).sort((a, b) => (a === none) - (b === none) || a.localeCompare(b, "de"));
    box.innerHTML = `<p class="muted" style="margin:6px 0 18px;font-size:14px;max-width:60ch">${tr("Was eine Lampe macht, wenn der Strom zurückkommt, zum Beispiel nach dem Wandschalter oder einem Stromausfall.")}</p>` +
      rooms.map((room) => `<div class="room"><h2>${esc(room)}</h2>${byRoom[room]
        .sort((a, b) => label(a).localeCompare(label(b), "de") || a.entity_id.localeCompare(b.entity_id))
        .map((e) => {
          const st = h.states[e.entity_id];
          return `<div class="row"><div class="name">${esc(label(e))}<small>${tr("Einschaltverhalten")}</small></div>
              <div class="segs" data-e="${esc(e.entity_id)}">${POWERUP.map(([v, txt]) => `<button data-v="${v}" aria-pressed="${st.state === v}">${tr(txt)}</button>`).join("")}
              ${st.state === "custom" ? `<button disabled aria-pressed="true">${tr("Eigene (Hue App)")}</button>` : ""}</div></div>`;
        }).join("")}</div>`).join("");

    box.querySelectorAll(".segs[data-e] button[data-v]").forEach((b) => b.addEventListener("click", () => {
      const ent = b.parentElement.dataset.e;
      b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      this._call("select", "select_option", { entity_id: ent, option: b.dataset.v });
    }));
  }
}

// ------------------------------------------------------------------ Karte
// type: custom:led-color-card
//   ansicht: verlauf | szenen | favoriten | einstellungen   (Start-Bereich)
//   ansichten: [verlauf, szenen]   oder   tabs: true        (mehrere Bereiche mit Reitern)
//   lampe: sensor.hue_plus_…_verlauf   lampenwahl: false     (feste Lampe, Auswahl ausblenden)
//   paar: sensor.hue_plus_…_verlauf    gespiegelt: true      (zweite Lampe macht mit)
//   raum: Wohnzimmer                                         (nur Szenen dieses Raums)
//   titel: "Licht Wohnzimmer"
class LedColorCard extends LedColorPanel {
  setConfig(config) {
    this._cfg = { ...(config || {}) };
    if (this._hass) { // Änderung im Karten-Editor: neu aufbauen
      this._shapeSig = this._chipSig = null; this._draft = null; this._hist = [];
      this._init();
    }
  }
  getCardSize() { return this._cfg?.ansicht === "szenen" ? 4 : 9; }
  getGridOptions() { return { columns: "full", min_columns: 6 }; }
  static getStubConfig() { return { ansicht: "verlauf" }; }
}

if (!customElements.get("led-color-panel")) customElements.define("led-color-panel", LedColorPanel);
if (!customElements.get("led-color-card")) {
  customElements.define("led-color-card", LedColorCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "led-color-card", name: "LED Color", description: "Farbverläufe, Szenen und Favoriten für Hue (LED Color für Hue)", preview: false });
}
console.info(`%c LED Color für Hue %c ${VERSION} `, "background:#e9c48a;color:#000;border-radius:4px 0 0 4px;padding:2px 4px", "background:#222;color:#e9c48a;border-radius:0 4px 4px 0;padding:2px 4px");
