# Smart Cleaner UI redesign: "Ultraviolet"

Date: 2026-11-18 · Status: awaiting approval · Scope: `frontend/` (plus new UI strings in `backend/app/i18n.py`)

## Intent

The current UI is coherent but reads as generic and "boring": a slate-and-blue
dashboard with dense spacing, a bare file input, one blue for every chart, and
numbers formatted differently from place to place. The goal is a distinctive,
modern identity for Smart Cleaner that still behaves like a precise data tool,
and that looks good in the oral defence and in screenshots for the report.

## Goals

- A brand identity: an SVG logo used in the header and as the favicon, a wordmark,
  and a palette and type system that are recognisably Smart Cleaner.
- Replace the plain `<input type="file">` with a drag-and-drop upload zone.
- More breathing room: a consistent 4px-based spacing scale, larger card padding,
  16px body text.
- One number-formatting rule applied everywhere (tables, stat cards, chart labels, hovers).
- Chart colours that carry meaning instead of one blue for everything.

## Non-goals

- No dark mode for now. Colours are tokens, so dark mode can be added later.
- No change to the four-step flow, the API calls, the session state, or what is
  computed. `App.jsx` state logic, `choices.js` and `api.js` stay as they are.
- No new npm dependencies: no component library, no icon package, no CSS framework.

## Anti-goals (failure even if it "works")

- Any behaviour regression: tab locking, choice tracking, preview staleness,
  apply/download invalidation, or keyboard access to the stepper and options.
- Decoration that hurts reading data: lime text on white, gradients behind tables,
  or colour as the only signal for severity.
- Hardcoded user-facing strings in the frontend (all text stays in `i18n.py`).

## Constraints

- `npm test`, `npm run lint`, `npm run build` and the backend `pytest` suite stay green.
- WCAG AA: text contrast ≥ 4.5:1, graphical marks ≥ 3:1, visible focus,
  `prefers-reduced-motion` respected.
- Works at 375px width with no horizontal page scroll (wide tables scroll inside their card).

## Approaches considered

Three directions were mocked up side by side (logo, palette, fonts, upload zone,
stats card, chart colours):

| | Direction | Trade-off |
|---|---|---|
| A | **Clean Lab**: deep teal + mint, Space Grotesk / Inter / JetBrains Mono, dark header | Calm and precise, but the closest to the current look |
| **B** | **Ultraviolet**: electric violet + lime, Sora / Plus Jakarta Sans / IBM Plex Mono, light header, rounded pill controls | Energetic and the most "modern product". Lime must stay decorative for contrast |
| C | **Terracotta Paper**: warm paper, espresso + terracotta, Fraunces serif | Most crafted and editorial, but the serif fights with dense tables |

**Chosen: B (Ultraviolet)**, picked by the user from the mockups.

## Design decisions

### Palette (CSS custom properties in `index.css`)

| Token | Value | Use |
|---|---|---|
| `--page` | `#F7F6FC` | app background (lilac paper) |
| `--surface` | `#FFFFFF` | cards, tables |
| `--surface-sunk` | `#F1EFFB` | stat tiles, hover rows |
| `--ink` | `#1B1630` | body text |
| `--ink-2` | `#4A4466` | secondary text |
| `--muted` | `#6B6585` | help text, axis labels (5.5:1 on white) |
| `--rule` / `--rule-strong` | `#E2DFF0` / `#CBC6E0` | borders |
| `--accent` | `#5B3DF5` | primary actions, active step, focus ring (6.1:1 on white) |
| `--accent-hover` | `#4A2FD6` | |
| `--accent-soft` | `#EEEAFE` | selected option, drop-zone hover |
| `--lime` | `#C6F432` | **decorative only**: logo, active-step dot. Never text on white |
| warn / error tokens | unchanged | severity, always paired with a text label |

### Chart colours (one meaning per colour)

| Series | Colour |
|---|---|
| Numeric histogram (and date histograms) | violet `#5B3DF5` |
| Categorical bars | teal `#0D9488` |
| Preview "before" | muted lilac-grey `#8E88AB` (3.4:1) |
| Preview "after" | violet `#5B3DF5` |
| Correlation heatmap | diverging: teal `#0B6B63` (−1) → `#4FB8AC` → neutral `#F4F3F8` (0) → `#9D8CF8` → violet `#4527C9` (+1) |

Chart colours live in one small JS module (`src/theme.js`) that mirrors the CSS
tokens, so `Chart.jsx` no longer hardcodes hex values. Plotly's font becomes Plus
Jakarta Sans. Axes and grid stay recessive (`--rule`).

### Typography

- Headings and wordmark: **Sora** 600/700, tight letter-spacing (−0.02em).
- Body and UI: **Plus Jakarta Sans** 400/500/600/700, base 16px, line-height 1.5.
- Numbers (stat values, numeric table cells, file summary counts): **IBM Plex Mono**
  500 with `tabular-nums`, right-aligned in tables.
- Loaded from Google Fonts in `index.html` (replacing Public Sans), `display=swap`.

### Spacing, shape and elevation

- Spacing tokens `--space-1..7` = 4, 8, 12, 16, 24, 32, 48px. Cards get 24px padding
  (16px under 560px) and the page gets 32px gaps between sections.
- Radii: 8px (inputs, chips), 12px (option tiles, stat tiles), 16px (cards), pill (buttons, tags, severity).
- One soft shadow for cards: `0 1px 2px rgb(27 22 48 / 6%), 0 4px 16px rgb(27 22 48 / 5%)`.
- Motion: 150–200ms colour/border transitions only. Disabled under reduced motion (already in place).

### Logo and header

- Logo: violet squircle (`rx=13` on a 40×40 box) with three faint lime dots
  (scattered data) resolving into a bold lime check stroke (clean data). Inline
  SVG component `Logo.jsx`, `aria-hidden`, with the wordmark text next to it from `ui.app.title`.
- `public/favicon.svg` is replaced with the same mark.
- Header: white with a bottom rule (no longer a dark masthead). The logo and wordmark
  sit with the subtitle, and the four-step stepper below keeps its tab semantics
  (`role="tablist"`, `aria-selected`, locked steps disabled). Active step: violet
  underline and a filled violet number. Completed steps keep their status line.

### Drag-and-drop upload (Import tab)

- A large dashed drop zone replaces the visible file input: upload icon (inline SVG),
  "Drag and drop your file here", accepted formats, and a "Browse files" pill.
- It is a `<label>` wrapping a visually hidden `<input type="file">` with the same
  `accept` list. Click, Enter and Space open the picker, and `:focus-within` shows the focus ring.
- `dragover` highlights the zone (`--accent-soft`, solid violet border, "Release to upload").
  `drop` takes the first file and calls the existing `send(f)`. Wrong file types are
  rejected by the backend exactly as today, and the error appears in the existing `ErrorAlert`.
- Disabled (dimmed, no drop) while uploading or analysing.
- After a file is loaded the zone collapses to a compact file row: name, rows and columns
  in mono, and a "Replace file" action that reopens the picker. Drop still works on it.
- New UI keys in `i18n.py` (e.g. `ui.import.drop_title`, `ui.import.drop_formats`,
  `ui.import.drop_browse`, `ui.import.drop_release`, `ui.import.replace`). The final names are the builder's.

### Number formatting (`format.js`)

One rule, applied everywhere:

- Counts and integers: thousands separators, no decimals (`12,480`).
- Other numbers: at most 4 significant figures with thousands separators (`1,284.6`, `0.5123`).
  Exponent form only below 1e-3 or at 1e7 and above (`5.00e-4`). Floating-point noise prints as `0`.
- Percent stats (`*_pct`): always suffixed with `%`, at most 2 decimals (`3.42%`, `0%`).
  New `fmtPct`, chosen per stat key by one helper (`fmtStat(key, value)`) so tables
  and stat cards cannot diverge.
- Correlations: always 2 decimals in cells, 3 in hovers (unchanged).
- Plotly hovers and bar labels use the same `fmt` output (passed through `customdata`/`text`)
  rather than Plotly's own `%{y:,}` formatting.
- New unit tests: `src/format.test.js`.

## Build order (one commit per step, stop and explain after each)

Branch `feat/ui-redesign` from the current `feat/extras` HEAD.

0. **Foundation:** tokens, fonts, spacing, base components (buttons, panels, tables,
   tags, alerts), `Logo.jsx` + favicon, header and stepper, `theme.js`, `format.js` + tests.
   Add `.superpowers/` to `.gitignore`.
1. **Import tab:** the drop zone, the file row, the settings and types panels restyled. Adds i18n keys.
2. **EDA tab:** the facts row as stat tiles, the stats table, chart colours and chart cards, the heatmap.
3. **Preprocessing tab:** the column index, column card, option tiles, and before/after preview colours.
4. **Export tab:** the summary tiles, actions and steps table.

After each step: `npm test`, `npm run lint`, `npm run build`, backend `pytest`, a manual
check in the browser, then commit (and push, per the usual per-group routine).

## Left to the builder

- Exact i18n key names and wording for the new upload strings.
- Fine-tuning of chart margins and stat-tile layout per tab, within the tokens above.
- Responsive details beyond: stepper 2×2 under 860px, single column under 560px, no page-level horizontal scroll.

## Calls made by Claude (please check)

- Light header instead of a dark masthead (follows the chosen mockup).
- Categorical charts in teal, and the heatmap in teal↔violet instead of blue↔red,
  so red stays reserved for errors.
- Before/after "before" grey darkened from the mockup (`#CFCBE0` → `#8E88AB`) to meet 3:1.
- Charts read colours from a JS `theme.js` mirror of the CSS tokens rather than reading CSS variables at runtime.
- No client-side file-type check on drop; the backend's existing validation and error message are used.
