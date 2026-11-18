# UI Redesign ("Ultraviolet") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the Smart Cleaner frontend in the approved Ultraviolet direction (brand, drop-zone upload, spacing, consistent numbers, meaningful chart colours) without changing behaviour.

**Architecture:** All visual tokens live as CSS custom properties in `frontend/src/index.css`. Chart colours are mirrored in a small `frontend/src/theme.js` used by `Chart.jsx`. Number display goes through `frontend/src/format.js` (`fmt`, `fmtInt`, `fmtPct`, `fmtStat`). New UI strings go in `backend/app/i18n.py`. No state or API code changes.

**Tech Stack:** React 19, Vite 8, Vitest 5 (node environment, no DOM library), Plotly via react-plotly.js, FastAPI backend serving labels.

**Spec:** `docs/superpowers/specs/2026-11-18-ui-redesign-design.md`

## Global Constraints

- No new npm dependencies. Icons are inline SVG.
- All user-facing text comes from `backend/app/i18n.py` via `t("ui....")`. The only exception is the boot error in `App.jsx`, which stays as it is.
- Light mode only. Colours are tokens on `:root`.
- Contrast: text ≥ 4.5:1, chart marks ≥ 3:1. Lime `#C6F432` is never used for text on a light background.
- Fonts: Sora 600/700 (headings), Plus Jakarta Sans 400/500/600/700 (body, 16px), IBM Plex Mono 400/500/600 (numbers, `tabular-nums`).
- Spacing tokens `--space-1..7` = 4/8/12/16/24/32/48px. Radii 8/12/16/pill.
- Heatmap: `zmin: -1, zmax: 1, zmid: 0`. The colour at 0 is neutral `#F4F3F8` (user requirement, 2026-11-18).
- Keep every existing class used for behaviour (`aria-*`, `role`, `hidden`, `disabled`) and the tablist semantics of the stepper.
- Gate after every task: from `frontend/`, `npm test`, `npm run lint`, `npm run build`; from `backend/`, `.venv/Scripts/python -m pytest -q`. All green.
- **Stop after each Step group (0–4)** so the user can check it in the browser. Restart the backend by hand after `i18n.py` edits (uvicorn reload misses OneDrive changes).

## Review Focus

1. A tiny but non-zero percentage (e.g. 0.004% missing) must not display as "0%". It shows "<0.01%" (test in Task 1).
2. A drag carrying no file (selected text, a link), or several files, must not crash: no file means ignore, several files means take the first (test in Task 5).
3. Picking the same file again after "Replace file" must upload again. Reset the input's `value` after each pick (manual check in Task 5).
4. A drop while uploading or analysing is ignored (manual check in Task 5).
5. The heatmap scale stays [−1, 1] with neutral at 0, whatever the data (test in Task 2).

---

## Step 0: Foundation

### Task 1: One number-formatting rule

**Files:**
- Modify: `frontend/src/format.js`
- Create: `frontend/src/format.test.js`

**Interfaces:**
- Produces: `fmt(value, missing = "") -> string`, `fmtInt(value) -> string` (unchanged signature), `fmtPct(value, missing = "") -> string`, `fmtStat(key: string, value, missing = "") -> string`.

- [ ] **Step 1: Write the failing tests** in `format.test.js`:

```js
import { describe, expect, test } from "vitest";
import { fmt, fmtInt, fmtPct, fmtStat } from "./format.js";

describe("fmt", () => {
  test("integers keep every digit, grouped", () => {
    expect(fmt(12480)).toBe("12,480");
    expect(fmt(123456)).toBe("123,456");
  });
  test("decimals: at most 4 significant figures", () => {
    expect(fmt(1284.5678)).toBe("1,285");
    expect(fmt(0.51234)).toBe("0.5123");
    expect(fmt(2.5)).toBe("2.5");
  });
  test("exponent only at the extremes", () => {
    expect(fmt(0.0005)).toBe("5.00e-4");
    expect(fmt(-0.00002)).toBe("-2.00e-5");
    expect(fmt(1e8)).toBe("1.00e+8");
  });
  test("noise, missing and text", () => {
    expect(fmt(1e-15)).toBe("0");
    expect(fmt(null, "—")).toBe("—");
    expect(fmt(NaN, "—")).toBe("—");
    expect(fmt("abc")).toBe("abc");
  });
});

describe("fmtPct", () => {
  test("suffix and two decimals at most", () => {
    expect(fmtPct(3.4215)).toBe("3.42%");
    expect(fmtPct(0)).toBe("0%");
    expect(fmtPct(100)).toBe("100%");
  });
  test("tiny non-zero values are not shown as 0%", () => {
    expect(fmtPct(0.004)).toBe("<0.01%");
  });
  test("missing", () => expect(fmtPct(null, "—")).toBe("—"));
});

describe("fmtStat", () => {
  test("routes by key", () => {
    expect(fmtStat("missing_pct", 3.4215)).toBe("3.42%");
    expect(fmtStat("outlier_pct", 0)).toBe("0%");
    expect(fmtStat("n_unique", 12480)).toBe("12,480");
    expect(fmtStat("mean", 0.51234)).toBe("0.5123");
    expect(fmtStat("skewness", null, "—")).toBe("—");
  });
});

test("fmtInt", () => expect(fmtInt(1234.6)).toBe("1,235"));
```

- [ ] **Step 2: Run** `npm test -- format` from `frontend/`. Expected: FAIL (`fmtPct`/`fmtStat` not exported, `fmt(1284.5678)` gives `1,284.568`).
- [ ] **Step 3: Implement.** In `fmt`: integers use the grouped formatter, other values `Intl.NumberFormat("en-US", { maximumSignificantDigits: 4 })`, with the existing noise/exponent thresholds kept. `fmtPct`: `0 < |v| < 0.01` gives `"<0.01%"`, otherwise `maximumFractionDigits: 2` plus `"%"`. `fmtStat`: keys ending in `_pct` go to `fmtPct`, keys starting with `n_` go to `fmtInt`, everything else to `fmt`.
- [ ] **Step 4: Run** `npm test`. Expected: all pass, including the existing suites.
- [ ] **Step 5: Commit** `feat(format): one number rule with fmtPct and fmtStat`.

### Task 2: Chart theme module

**Files:**
- Create: `frontend/src/theme.js`, `frontend/src/theme.test.js`

**Interfaces:**
- Produces: `export const CHART = { numeric: "#5B3DF5", categorical: "#0D9488", before: "#8E88AB", after: "#5B3DF5", ink2: "#4A4466", ink: "#1B1630", grid: "#ECEAF5", axis: "#CBC6E0", surface: "#FFFFFF", font: "Plus Jakarta Sans, system-ui, sans-serif" }` and `export const DIVERGING = [[0, "#0B6B63"], [0.25, "#4FB8AC"], [0.5, "#F4F3F8"], [0.75, "#9D8CF8"], [1, "#4527C9"]]`.

- [ ] **Step 1: Write the failing test** `theme.test.js`: `DIVERGING[0][0] === 0`, `DIVERGING.at(-1)[0] === 1`, `DIVERGING[2]` deep-equals `[0.5, "#F4F3F8"]`, the stops are strictly increasing, and `CHART.numeric !== CHART.categorical` and `CHART.before !== CHART.after`.
- [ ] **Step 2: Run** `npm test -- theme`. Expected: FAIL (module missing).
- [ ] **Step 3: Create `theme.js`** with the values above and a header comment saying it mirrors `index.css` tokens.
- [ ] **Step 4: Run** `npm test`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(theme): chart colour tokens with a neutral-zero diverging scale`.

### Task 3: Design tokens, fonts and base components

**Files:**
- Modify: `frontend/index.html` (font link), `frontend/src/index.css` (`:root` and base sections: type, panel, field, buttons, alerts, tags, severity, tables), `.gitignore` (add `.superpowers/`)

**Interfaces:**
- Produces CSS tokens used by every later task: `--page --surface --surface-sunk --ink --ink-2 --muted --rule --rule-strong --accent --accent-hover --accent-soft --lime --teal`, warn/error tokens unchanged, `--space-1..7`, `--radius-s: 8px --radius-m: 12px --radius-l: 16px --radius-pill: 999px`, `--shadow-card`, `--font-display --font-body --font-mono`, and a `.num-mono` utility (mono, tabular, weight 500).

- [ ] **Step 1:** Replace the Public Sans link with `https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap`.
- [ ] **Step 2:** Rewrite `:root` with the spec palette and tokens. Body is 16px Plus Jakarta Sans. `h1–h4` use `--font-display`. `.panel` gets `--radius-l`, 24px padding and `--shadow-card`. `.btn` and `.tag` become pills, `.btn-primary` is violet. `.data-table td.num, th.num` use the mono font. Focus ring: 2px `--accent`. Keep every existing class name.
- [ ] **Step 3:** Add `.superpowers/` to `.gitignore`. Stage only that line: the user's other uncommitted `.gitignore` lines stay unstaged (`git add -p`).
- [ ] **Step 4: Gate** (test, lint, build, pytest). Expected: all green.
- [ ] **Step 5: Commit** `style: Ultraviolet tokens, fonts and base components`.

### Task 4: Logo, favicon and header

**Files:**
- Create: `frontend/src/components/Logo.jsx`
- Modify: `frontend/public/favicon.svg`, `frontend/src/App.jsx` (masthead markup only), `frontend/src/index.css` (masthead and stepper section)

**Interfaces:**
- Produces: `export default function Logo({ size = 36 })` that renders an `aria-hidden` inline SVG: a violet squircle (40×40 viewBox, `rx=13`, `#5B3DF5`), three lime dots (opacity .4–.6) and a lime check path `M11 21.5l6.5 6.5L31 13`, stroke-width 4.2, round caps.

- [ ] **Step 1:** Create `Logo.jsx`. Write the same mark to `favicon.svg` (standalone `xmlns`).
- [ ] **Step 2:** In `App.jsx`, render `<Logo />` before the `h1` inside `.brand`. No state or handler changes.
- [ ] **Step 3:** CSS: white masthead with a 1px `--rule` bottom border. Brand row: logo, Sora wordmark (`h1`, 1.3rem, 700) and subtitle in `--muted`. Stepper: inactive steps in `--muted`. The active step has a 3px `--accent` underline and a filled violet index with white text. A small lime dot (`::after`, 6px) marks the active index. Locked steps are at 0.45 opacity. Keep the 2×2 layout under 860px and hide the status line under 560px.
- [ ] **Step 4: Gate.** Then run the app (backend and `npm run dev`) and check: the favicon shows in the tab, Tab/Enter moves through the steps, and locked steps can't be clicked.
- [ ] **Step 5: Commit** `feat(brand): Smart Cleaner logo, favicon and light header`.

**STOP: the user checks Step 0 in the browser.**

---

## Step 1: Import tab

### Task 5: Drag-and-drop upload zone

**Files:**
- Create: `frontend/src/components/DropZone.jsx`, `frontend/src/dropzone.js`, `frontend/src/dropzone.test.js`
- Modify: `frontend/src/tabs/ImportTab.jsx` (the file field only), `backend/app/i18n.py`, `frontend/src/index.css` (import section)
- Test: `backend/tests/test_i18n.py`

**Interfaces:**
- Produces: `pickDroppedFile(dataTransfer) -> File | null` in `dropzone.js` (null when there are no files or `dataTransfer` is null, otherwise `files[0]`).
- Produces: `export default function DropZone({ onFile: (File) => void, disabled: boolean, file: { name, summary } | null })`. It renders the large zone when `file` is null and the compact file row otherwise. Both are drop targets.
- New i18n keys: `ui.import.drop_title` ("Drag and drop your file here"), `ui.import.drop_formats` (".csv · .txt · .xlsx · .xls"), `ui.import.drop_browse` ("Browse files"), `ui.import.drop_release` ("Release to upload"), `ui.import.replace` ("Replace file").

- [ ] **Step 1: Failing tests.** `dropzone.test.js`: `pickDroppedFile(null)` is null; `pickDroppedFile({ files: [] })` is null; `pickDroppedFile({ files: [a, b] })` is `a`. In `test_i18n.py`, `test_drop_zone_labels_exist` asserts that the five keys are in `ui_labels()`.
- [ ] **Step 2: Run** both suites. Expected: FAIL.
- [ ] **Step 3: Implement.** Add the keys to `i18n.py`. `DropZone` is a `<label htmlFor="file">` wrapping the existing `<input id="file" type="file" accept=".csv,.txt,.xlsx,.xls">` with the `.visually-hidden` class. `onDragOver`/`onDragEnter` call `preventDefault()` and set `dragging` (unless disabled). `onDragLeave` clears it. `onDrop` calls `preventDefault()`, then `pickDroppedFile(e.dataTransfer)`, then `onFile` (unless disabled). The input's `onChange` calls `onFile` and then sets `e.target.value = ""`. The upload icon is an inline SVG with `aria-hidden`. Keep the `ui.import.file` label as the zone's accessible name and `ui.import.file_help` as help text. In `ImportTab`, replace the `<input>` and file summary with `<DropZone onFile={(f) => { setFile(f); send(f); }} disabled={busy != null} file={...} />`, keeping the `uploading` status line.
- [ ] **Step 4: Run** both suites. Expected: PASS. Gate.
- [ ] **Step 5: Manual check:** click, keyboard (Tab then Space) and drop all upload. Dropping text does nothing. Dropping while "Reading the file…" is showing is ignored. "Replace file" with the same file uploads again. A `.pdf` drop shows the backend error in `ErrorAlert`.
- [ ] **Step 6:** Restyle the rest of the Import tab (settings panel, mode choices as option tiles, the types table) with tokens only. Gate.
- [ ] **Step 7: Commit** `feat(import): drag-and-drop upload zone`.

**STOP: the user checks Step 1 in the browser.**

---

## Step 2: EDA tab

### Task 6: Chart colours by meaning

**Files:**
- Modify: `frontend/src/components/Chart.jsx`

**Interfaces:**
- Consumes: `CHART`, `DIVERGING` (Task 2), `fmt` (Task 1).
- Produces: `Chart({ chart, height = 220, tone = "default" })`. `tone` is `"default" | "before" | "after"`. With `"default"`, histograms use `CHART.numeric` and categorical bars use `CHART.categorical`. With `"before"`, both use `CHART.before`. With `"after"`, both use `CHART.after`. `Heatmap` keeps its signature.

- [ ] **Step 1:** Remove the hardcoded colour constants and import from `theme.js`. The heatmap uses `DIVERGING` with `zmin: -1, zmax: 1, zmid: 0` unchanged.
- [ ] **Step 2:** Hovers show counts through `fmt`: pass the formatted counts in `customdata` alongside the range or label, so `%{y:,}` and `%{x:,}` are gone.
- [ ] **Step 3: Gate.** Then check in the browser: numeric charts are violet, categorical charts teal, and on the heatmap 0 is pale grey and the colour bar runs −1…1.
- [ ] **Step 4: Commit** `feat(charts): colours by meaning and one number format in hovers`.

### Task 7: EDA layout and stats

**Files:**
- Modify: `frontend/src/tabs/EdaTab.jsx`, `frontend/src/index.css` (EDA section)

- [ ] **Step 1:** The stats table uses `fmtStat(k, v, dash)` instead of `fmt`. The class-ratio fact keeps `fmt`.
- [ ] **Step 2:** CSS: `.facts` become stat tiles (`--surface-sunk`, `--radius-m`, uppercase 11px `dt`, mono 1.15rem `dd`, `overflow-wrap: anywhere`). Chart cards get `--radius-m`, a 16px gap and 16px padding. The sticky header and `cell-warn` are kept.
- [ ] **Step 3: Gate**, then check the browser at 375px and 1440px. Expected: no page-level horizontal scroll, and long column names wrap in the tiles.
- [ ] **Step 4: Commit** `style(eda): stat tiles, consistent stats and roomier chart grid`.

**STOP: the user checks Step 2 in the browser.**

---

## Step 3: Preprocessing tab

### Task 8: Column card, options and preview

**Files:**
- Modify: `frontend/src/components/ColumnCard.jsx`, `frontend/src/index.css` (preprocessing section)

- [ ] **Step 1:** The key stats and the compare table use `fmtStat(k, v, dash)`. The "before" chart gets `tone="before"` and the "after" chart `tone="after"`.
- [ ] **Step 2:** CSS: column index active item in `--accent-soft` with a violet left bar. Option tiles get `--radius-m`, and the chosen tile a violet border, `--accent-soft` and an inset ring. Key stats become stat tiles like the EDA ones. The stale preview keeps `opacity: .55`.
- [ ] **Step 3: Gate**, then check the browser: choose an option, the preview goes stale and then refreshes, and the before chart is grey while the after chart is violet.
- [ ] **Step 4: Commit** `style(prep): option tiles, stat tiles and before/after colours`.

**STOP: the user checks Step 3 in the browser.**

---

## Step 4: Export tab

### Task 9: Export summary and actions

**Files:**
- Modify: `frontend/src/tabs/ExportTab.jsx` (class names only if needed), `frontend/src/index.css` (export section)

- [ ] **Step 1:** CSS: the summary and result `.facts` reuse the stat tiles. Step chips become 8px-radius chips on `--surface-sunk`. The download link keeps `.btn` and becomes primary once applied.
- [ ] **Step 2: Gate**, then check the browser: Apply, then Download, works. Changing a choice afterwards disables Download again.
- [ ] **Step 3: Commit** `style(export): summary tiles and actions`.

**STOP: the user checks Step 4. Then run the whole-branch review.**
