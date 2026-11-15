# Frontend

## Purpose

`app/frontend/` is the PlumeTrace control-room web app: React + TypeScript + Vite. Phase 1 Task 5
delivers only the scaffold: a top bar with the product name and a "Simulated" label, an empty
station region, the design tokens, lint, type-check, tests, build and the Vercel security headers
(recorded for a later phase; see [DEPLOYMENT.md](DEPLOYMENT.md)). Design reference: section 9;
visual rules: `.ux-profile.md`.

## Stack and pinned versions

Exact versions are in `app/frontend/package.json` and `package-lock.json`; the full table is in
[LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md#pinned-versions).

| Package | Version |
|---|---|
| react, react-dom | 19.3.1 |
| vite, @vitejs/plugin-react | 8.3.8, 6.3.0 |
| tailwindcss, @tailwindcss/vite | 4.3.5 |
| typescript | 6.0.3 (not 7.x: typescript-eslint 8.72.2 needs `<6.1`) |
| eslint, typescript-eslint | 10.14.0, 8.72.2 |
| vitest, @vitest/coverage-v8 | 5.1.0 (the two must match) |
| jsdom | 29.1.1 (30+ needs Node 22.22 or newer) |
| @testing-library/react, dom, jest-dom | 16.3.3, 10.4.2, 7.0.1 |
| @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono | 5.3.0 |
| clsx, tailwind-merge, class-variance-authority | 2.1.1, 3.7.0, 0.7.1 |
| lucide-react, radix-ui | 1.72.0, 1.8.1 |
| zustand | 5.1.0 |
| shadcn CLI (run with `npx`, not installed) | 4.23.0 |

Node `>=22.13.0` (`engines` in `package.json`).

## Scripts

Run from `app/frontend/`.

| Script | What it does |
|---|---|
| `npm run copy:replay` | Copy `app/replay/` to `public/replay/` (git-ignored); runs before `dev`, `build` and `build:replay` |
| `npm run dev` | Vite dev server on `http://localhost:5173`; `npm run dev -- --mode replay` runs without the backend |
| `npm run build` | Type-check, then `vite build` into `dist/` (git-ignored); the live build |
| `npm run build:replay` | Copy replay files, type-check, `vite build --mode replay` (no live-API code) |
| `npm run check:replay-bundle` | `scripts/check-replay-bundle.mjs`: fails if a `dist/assets/*.js` file contains `/api/` or if none contains `/replay/scenarios` (the ReplaySource must really be in the bundle); prints `replay bundle OK` |
| `npm run preview` | Serve `dist/` locally |
| `npm run lint` | ESLint (typescript-eslint, react-hooks, react-refresh, jsdoc) |
| `npm run typecheck` | `tsc --noEmit` (strict, `noUncheckedIndexedAccess`) |
| `npm run test` | Vitest, one run |
| `npm run test:coverage` | Vitest with v8 coverage; thresholds lines 80, functions 80, branches 70, statements 80 |
| `npm run gen:types` | `json2ts` (json-schema-to-typescript 16.0.0): `contract.schema.json` to `contract.ts` (see Type contract) |

## Folder rules

`src/` may contain only `main.tsx`, `vite-env.d.ts`, `app/`, `features/`, `shared/` and `styles/`.
`check_structure.py` enforces it, together with the size limits (TS/TSX file at most 250 lines,
tests at most 400). A feature folder is used through its `index.ts` only. The full rules are in the
`frontend-structure` skill.

- `src/app/` holds `AppShell.tsx` (the top-level layout), `TopBar.tsx` and `WindReadout.tsx`. `scripts/` (next to `src/`) holds `check-replay-bundle.mjs`.
- `src/shared/testing/setup.ts` is the Vitest setup file (jest-dom matchers, cleanup after each test);
  `replayFixture.ts` builds a valid replay for tests.
- `src/shared/data/`, `src/shared/playback/` and `src/shared/selection/` are the data layer (see
  Data layer); each has an `index.ts` that is its public API.
- `src/shared/lib/` holds `cn.ts` (class merging) and `format.ts` (units and time formatting).
- `src/shared/ui/` holds the shadcn primitives (lower-case file names, generated) and our own
  shared primitives `Panel.tsx` and `StatusBadge.tsx` (PascalCase).
- `src/styles/index.css` imports Tailwind and defines the design tokens.
- The `@/` alias points to `src/` (`tsconfig.json` `paths`, `vite.config.ts` `resolve.alias`).

## Design system

Final since Phase 4 Task 2. Everything lives in `src/styles/index.css`; components use token
classes (`bg-surface-1`, `text-text-2`, `border-border-1`), never raw hex or `bg-[var(--x)]`.

### Colour tokens

Surfaces are grey in four levels, separated by 1 px borders rather than shadows. Colour is
reserved for meaning (ISA-101 spirit). Contrast ratios are computed (WCAG 2.x relative luminance).

| Token | Value | Meaning | Contrast on surface-0 / surface-1 |
|---|---|---|---|
| `--surface-0` | `#15171a` | App background, 3D view surround | n/a |
| `--surface-1` | `#1c1f23` | Panel body | n/a |
| `--surface-2` | `#24282d` | Raised controls, dialogs | n/a |
| `--surface-3` | `#2d3238` | Hover and selected rows | n/a |
| `--border-1` | `#343a41` | Panel and divider lines | 1.4 on surface-1 (decorative) |
| `--border-2` | `#4a515a` | Control outlines | 2.1 on surface-1 |
| `--text-1` | `#e8eaed` | Primary text and values | 14.9 / 13.7 |
| `--text-2` | `#a9b0b8` | Secondary text, units, panel titles | 8.2 / 7.6 |
| `--text-3` | `#7c848d` | Tertiary, disabled | 4.7 / 4.4 |
| `--accent` | `#5b8db8` | The one action hue (primary buttons) | 5.1 / 4.7 |
| `--accent-contrast` | `#0f1b26` | Text on `--accent` | 4.9 on accent |
| `--focus` | `#8fb8de` | Focus ring (`:focus-visible`, 2 px, offset 2 px) | 8.6 / 7.9 |
| `--alarm-high` | `#d9534f` | Alarm priority high | 4.5 / 4.2 |
| `--alarm-med` | `#e8a33d` | Alarm priority medium | 8.3 / 7.7 |
| `--alarm-low` | `#c8b44a` | Alarm priority low | 8.6 / 7.9 |
| `--ok` | `#4e9f70` | Normal, approved, healthy | 5.6 / 5.1 |
| `--candidate` | `#f0a202` | AI-located leak candidate | 8.4 / 7.8 |
| `--ch4-0` to `--ch4-4` | `#f6e8a6`, `#f3c063`, `#e8893a`, `#d4502e`, `#a61e22` | Methane concentration ramp, low to high, colour-blind safe, sequential | data colours |
| `--plume-tint` | `#cbc3b2` | Plume particle tint; methane is invisible, so the overlay is a labelled visualisation | data colour |

Rules that follow from the numbers:

- `--text-3` falls below 4.5:1 on surface-1 and below. Use it only for non-essential or disabled
  text on surface-0, never for a value, unit or label an operator must read.
- `--alarm-high` as text is 4.2:1 on surface-1. State and priority are carried by the marker shape
  and the word (see `StatusBadge`), the colour only reinforces them.
- `--ch4-3` and `--alarm-high` are both red-orange. A concentration colour must never be the only
  sign of an alarm, and an alarm must never be shown as a concentration colour.

Tailwind classes come from the `@theme` block: `bg-surface-0..3`, `border-border-1|2`,
`text-text-1|2|3`, `bg-accent`, `bg-alarm-high|med|low`, `bg-ok`, `bg-candidate`. The `--ch4-*` and
`--plume-tint` tokens are read by the 3D and chart code through `var()`.

### Typography

IBM Plex Sans (interface) and IBM Plex Mono (tags such as K-202 and PIC-101, values, timestamps),
chosen as an engineering-drawing family with true tabular figures. Licence: SIL Open Font
License 1.1 (package licence `OFL-1.1`, @fontsource 5.3.0). Files come from the npm packages
`@fontsource/ibm-plex-sans` (400, 500, 600) and `@fontsource/ibm-plex-mono` (400, 500), imported in
`src/main.tsx` and bundled by Vite: no font is fetched from a network at run time.

| Class | Size / line height | Use |
|---|---|---|
| `text-xs` | 12 / 16 | Units, badges, table meta |
| `text-sm` | 13 / 18 | Panel titles, table cells |
| `text-base` | 14 / 20 | Body (set on `html`) |
| `text-md` | 16 / 22 | Section headings |
| `text-lg` | 20 / 26 | Dialog titles |
| `text-xl` | 24 / 30 | KPI values |

Numbers use `font-mono` or `tabular-nums` and always carry their unit in a quieter weight.

### Shape, focus, motion

- Radius: `--radius` 4 px (`rounded-sm`, also `rounded-md`); dialogs and tab lists 6 px
  (`rounded-lg`). No larger radius on product surfaces.
- Focus: every `:focus-visible` gets a 2 px `--focus` outline with a 2 px offset.
- Reduced motion: under `prefers-reduced-motion: reduce` animation and transition durations
  drop to 0.01 ms.

### shadcn primitives

Config: `app/frontend/components.json` (style `new-york`, Radix, Tailwind v4, no `tailwind.config`,
icons `lucide`). Aliases map components and ui to `@/shared/ui`, utils to `@/shared/lib/cn`.
Added with the pinned CLI: `npx --yes shadcn@4.23.0 add <name>` run from `app/frontend`. Present:
`button`, `dialog`, `tooltip`, `tabs`, `separator`, `scroll-area`.

Rules:

- shadcn's semantic names are mapped onto our tokens in the `@theme inline` block of `index.css`
  (`background` is surface-2, `foreground` text-1, `muted` surface-3, `muted-foreground` text-2,
  `primary` accent, `primary-foreground` accent-contrast, `secondary` surface-3, `destructive`
  alarm-high, `border` border-1, `input` border-2, `ring` focus). There is no second palette.
- `--color-accent` stays our action hue, so the shadcn "hover surface" role is not `accent`:
  `button.tsx` (outline, ghost), `dialog.tsx` (close button) and `tooltip.tsx` use `surface-3`
  directly. Re-adding a component with `--overwrite` loses these edits; redo them from this list.
- Edits to generated files are limited to token classes, import paths and a TSDoc line per
  export (the lint rule requires it). The CLI wrote `from "cn"` and added an npm package `cn`
  for the `utils` alias; the imports were changed to `@/shared/lib/cn` and the package removed.
- Lucide icons only, monochrome. `TooltipProvider` must wrap the app when the first tooltip is used.

### Shared primitives

- `Panel({ title, actions?, children, className? })`: `<section aria-labelledby>` with a 32 px
  header, 1 px `border-border-1` border, `bg-surface-1`, scrolling body.
- `StatusBadge({ tone, children })`: tones `high`, `med`, `low`, `ok`, `neutral`; a 6 px square
  marker plus text, never colour alone.

### Formatting helpers (`src/shared/lib/format.ts`)

| Function | Result |
|---|---|
| `formatPpm(v)` | `"4.2 ppm"` below 100, `"123 ppm"` from 100; `"—"` for null or non-finite |
| `formatRate(kgPerHour)` | `"14.2 kg/h"`; `"—"` for null or non-finite |
| `formatUtc(simStartUtc, t)` | `"HH:MM:SS UTC"`; `"—"` for an invalid start or non-finite `t` |
| `formatClock(t)` | `"+HH:MM"` elapsed; `"—"` for non-finite `t` |
| `compass16(fromDeg)` | one of 16 compass names, 22.5 degree sectors centred on the point |

Display rules owned by the callers (Gate 3 owner decisions, 2026-11-15):

- Every clock shows a zone label. `formatUtc` always ends in `UTC`. A station-local time gets its
  own label `UTC+5 station time`. `formatClock` is an elapsed duration, not a time of day, and must
  be labelled as elapsed.
- A leak rate is shown only as an interval, `p05-p95 kg/h (median p50)`, 2 significant figures,
  labelled `model estimate`. `formatRate` formats one number to one decimal and cannot enforce
  that; components call it per interval bound and add the interval and the label (a later task
  owns that component). Never show a bare rate.
- Replay `keyframes[].sources` drives the plume visual only and is never rendered as text.

### Evidence

`docs/evidence/2026-11-phase-4-tokens.png`: 1440x900 screenshot of the dev server with a token
and type-scale specimen injected into the DOM for the screenshot only (no specimen code is in the
repo).

## Data layer

Every feature gets scenario data through one interface in `src/shared/data/`. Features import
`@/shared/data`, `@/shared/playback` and `@/shared/selection` only, never an inner file. The three
stores are business-neutral containers; the shell and features read them through hooks.

### The `DataSource` interface

```ts
interface DataSource {
  readonly mode: "live" | "replay";
  listScenarios(signal?: AbortSignal): Promise<ReplayIndexEntry[]>;   // sorted by id
  loadScenario(id: string, signal?: AbortSignal): Promise<ReplayScenario>;
}
```

The types come from the generated contract (`ReplayScenario`, `ReplayIndex`, `ReplayIndexEntry`);
none is redeclared. Phase 5 adds agent runs to the same interface.

| Implementation | Reads | Used when |
|---|---|---|
| `ReplaySource` | `/replay/scenarios/index.json`, `/replay/scenarios/<id>.json` (static files) | `import.meta.env.MODE === "replay"` |
| `LiveSource` | `GET /api/scenarios`, `GET /api/scenarios/<id>/replay` (FastAPI through the Vite proxy) | every other mode (`npm run dev`, `npm run build`) |

Both check the id against `^s[0-9]+_[a-z0-9_]+$` before building a URL (`not_found` without a
request), validate the body with `parseReplayScenario` / `parseReplayIndex` (`validateReplay.ts`)
and accept a `ReplayIndex` object or a bare array as the scenario list (the live API answers a bare
array). `fetchJson.ts` is the only code that calls `fetch`.

### Error kinds

Every method rejects with `DataSourceError(kind, message)`; the UI chooses its text from `kind` and
never shows `message` verbatim. An aborted request re-throws the original `AbortError`, which the
store ignores.

| `kind` | Meaning | Raised when |
|---|---|---|
| `unreachable` | No server answered | `fetch` rejected, or any non-OK status other than 404 (the Vite proxy answers 5xx while the backend is down) |
| `not_found` | The id or file does not exist | status 404, or an id that is not a scenario id |
| `invalid` | The answer is not a usable replay | body is not JSON, or a check in `validateReplay.ts` failed (schema version, `simulated`, id, `step_s`, list lengths, units) |

Required UI state (Phase 4 review focus 1): with the backend down in live mode the panels show
"Backend not reachable" with the start command, not a crash. `error.kind === "unreachable"` selects
that state. Verified by hand on 2026-11-15: with the backend running, `GET /api/scenarios` through
the Vite dev server answered 200 with the three scenarios; after stopping the backend the same
request answered 502, which `fetchJson` maps to `unreachable`.

### Choosing the source: `getDataSource()`

`getDataSource()` returns a memoised `Promise<DataSource>`. `vite build --mode replay` replaces
`import.meta.env.MODE` with `"replay"`, so the live branch and its dynamic `import("./LiveSource")`
are dropped from the bundle. `data/index.ts` deliberately does not export the two classes: a
static import would pull `LiveSource` into the replay bundle. `npm run check:replay-bundle`
(`scripts/check-replay-bundle.mjs`) reads every `dist/assets/*.js` and fails when one contains the
`/api/` string and, so that the check cannot pass vacuously, also when no file contains
`/replay/scenarios` (the ReplaySource URL). Since Phase 4 Task 4 the shell (`useScenarioBootstrap`)
calls `getDataSource()` at startup, so the data layer is in the bundle. Negative control: a
non-replay `npm run build` makes the check exit 1 (a `LiveSource` chunk with `/api/`, no
`ReplaySource`); `src/app/checkReplayBundle.test.ts` pins the pass, both failures and a missing
folder with synthetic bundle folders.

Replay files are copied from `app/replay/` to `app/frontend/public/replay/` (git-ignored) by
`npm run copy:replay`, which runs before `dev`, `build` and `build:replay`.

### Stores

| Store | State | Actions |
|---|---|---|
| `useScenarioStore` (`data/scenarioStore.ts`) | `index`, `indexStatus`, `activeId`, `scenario`, `status` (`idle`, `loading`, `ready`, `error`), `error`, `requestSeq` | `loadIndex(source)`, `selectScenario(source, id)` |
| `useClockStore` (`playback/clockStore.ts`) | `tSeconds`, `durationS`, `playing`, `speed` | `play`, `pause`, `setSpeed`, `seek`, `reset`, `tick` |
| `useSelectionStore` (`selection/selectionStore.ts`) | `selectedTag`, `hoveredTag` | `select(tag or null)`, `hover(tag or null)` |

Hooks: `useActiveScenario()`, `useScenarioStatus()`, `useSampleIndex()`, `usePlaybackLoop()`.

`selectScenario` is the rule behind "a switch never mixes old and new data": abort the previous
request; increment `requestSeq`; set `activeId`, `scenario: null`, `status: "loading"`,
`error: null`; reset the clock to 0 (paused, duration 0); load; only when `requestSeq` still equals
this call's number set `scenario` and `status: "ready"` and reset the clock to the scenario's
`duration_s`. A slow earlier response, or a late failure of it, is dropped. `loadIndex` sets
`indexStatus` and, on failure, `error` (kind `unreachable` when the backend is down); `error` always
holds the most recent failure. Selecting the already-selected tag clears the selection; `hover` is
independent of it.

### Playback rules

- Speeds `SPEEDS = [1, 10, 60, 120]` (simulated seconds per real second), default 60;
  `SAMPLE_STEP_S = 60`.
- `play()` does nothing on an empty timeline (`durationS === 0`); at the end it restarts from 0.
- `reset(durationS)` sets `t = 0`, pauses and keeps the speed. `seek(t)` clamps to
  `[0, durationS]` and ignores a non-finite `t`.
- `tick(dtRealS)` adds `dtRealS * speed` while playing, stops at the end and ignores a step that is
  not in `(0, 1]` s: a tab that slept must not make the clock jump (1 s gap guard).
- The clock is the single time source. Panels re-render once per 60 s sample: `useSampleIndex()`
  selects `clamp(floor(t / 60), 0, n - 1)` with `n = max(1, round(durationS / 60))`. It is a
  number, so React re-renders only when the index changes. The 3D layer reads
  `useClockStore.getState()` inside `useFrame`; nothing animates through React state.
- `usePlaybackLoop()` is one `requestAnimationFrame` loop that calls `tick((now - last) / 1000)`;
  `AppShell` mounts it once (Phase 4 Task 4). It holds no React state and cancels on unmount.

### What the data layer must not expose

A loaded scenario also holds `keyframes[].sources` (`anchor_id`, `rate_kg_h`): the simulation input
used only to draw the plume. It is not a measurement and not an estimate. No store selector or
hook returns it as text, and nothing passes it to a format helper; views must not render it. The
data layer stores no rate. Any rate display must follow R1 to R4 (see `formatRate` under
Formatting helpers), and every clock shown carries a zone label (`formatUtc` ends in " UTC";
`formatClock` is elapsed time).

### Data layer tests

`data/*.test.ts` covers validation, both sources, `fetchJson`, `getDataSource` (and that the two
classes are not exported), and the store (stale response, typed error, backend down, switch during
playback, abort). `playback/*.test.ts(x)` covers the clock rules, the sample-index re-render rule
and the rAF loop; `selection/selectionStore.test.ts` the selection. `src/shared/testing/replayFixture.ts`
builds a small valid `ReplayScenario` (10 samples). Docs checked on 2026-11-15 (Context7): Zustand
v5.0.14 (latest listed there; the repo pins 5.1.0 exactly; `create<T>()(...)`, `getInitialState`,
`setState`, `getState`) and Vite 8.3.5 (`import.meta.env.MODE`, `--mode`, static replacement for
tree shaking).

## Layout and panels

Phase 4 Task 4. `src/app/AppShell.tsx` is a CSS grid, `grid-rows-[48px_minmax(0,1fr)_220px_44px]`:
top bar, working area, trends, playback bar. The working area is
`grid-cols-[320px_minmax(0,1fr)_360px]` from 1280 px wide (alarms, `<main aria-label="Station view">`,
station log); below 1280 px the station log moves under the alarms in the left column. Panels are
separated by 1 px `border-border-1` lines (no gaps, no shadows; the shared `Panel` border is
overridden per side). The station view is empty until the 3D scene arrives (Tasks 8 and 9) and
shows the scenario load status. `AppShell` mounts once: `useScenarioBootstrap()` (calls
`getDataSource()`, loads the list, opens the scenario), `usePlaybackLoop()` and `usePlaybackKeys()`.

| Panel | File | Data | Notes |
|---|---|---|---|
| Top bar | `app/TopBar.tsx` | `useCurrentConditions`, active scenario, clock | `PlumeTrace`, `Station <site id from ks07.json>`, scenario picker, mode (`Live · local backend` / `Replay`), wind, UTC clock, `Simulated` label (always visible) |
| Wind readout | `app/WindReadout.tsx` | `useCurrentConditions()` (`shared/data`) | `Wind 3.5 m/s from WSW (250°) · Stability D`; `Wind —` without data |
| Alarms | `features/alarms/components/AlarmList.tsx`, `AlarmRow.tsx` | `visibleEvents(scenario, t)` | Newest first; badge `Methane rise` (tone `med`: all detection events until Phase 5 triage gives priorities) with marker and word, sensor id, UTC time the window closed, `10-min mean .. ppm · baseline .. ppm · downwind of site`; a row click selects the sensor and seeks to the close time; selected row `aria-current="true"`; `<ul aria-live="polite" aria-label="Alarm list">` |
| Station log | `features/alarms/components/StationLog.tsx` | `scenario.log` with `t_s <= t` (exact clock time; a primitive selector returns the count of written entries, so the panel re-renders only when an entry appears) | Newest first; UTC time, kind label, tag, text |
| Trends | `features/trends/components/TrendsPanel.tsx`, `UPlotChart.tsx` | `chartData.ts` | See Chart rules |
| Playback bar | `features/scenarios/components/PlaybackBar.tsx` | clock store | Play/Pause, speeds 1/10/60/120x (`radiogroup`), scrubber (step 60 s) with a 4 px `--alarm-med` tick at every alarm close time, readout `Elapsed +02:20 · 02:20:00 UTC`; all controls disabled until the scenario is `ready` |
| Scenario status | `features/scenarios/components/ScenarioStatus.tsx` | scenario store (`status`, `error.kind`) | `Loading scenario…`; `unreachable` + live (the backend text is shown only for kind `unreachable`; a missing kind gives `Scenario could not be loaded.` + `Retry`): heading `Backend not reachable`, `Start it from the app folder:`, the command from LOCAL_DEVELOPMENT.md, `Retry`; `unreachable` + replay: `Replay files could not be loaded.` + `Retry`; `not_found`: `Scenario not found.`; `invalid`: `Scenario file is invalid. Regenerate it with scripts/export_scenarios.py.` |

`visibleEvents`: an event is visible when `window_start_s + EVENT_WINDOW_S (600) <= t`, sorted by
window start descending, ties by sensor id. Panels read the clock at whole-minute resolution
(`floor(t / 60) * 60`, a number selector), so they re-render once per simulated minute, except the
Station log, which compares entries with the exact clock time (a count selector); the UTC
clock and the elapsed readout update once per whole simulated second (two tiny components).

### Copy and display rules

- Every time carries its zone: `formatUtc` always ends in ` UTC`; `formatClock` is elapsed time and
  is always printed after the word `Elapsed`; the top-bar clock shows `— UTC` without a scenario.
  No station-local clock is shown in this task (it would be labelled `UTC+5 station time`).
  The S1 start is 00:00 UTC (about 05:00 local): never show a bare time.
- Empty and loading text uses `text-text-2`: `--text-3` is for disabled controls and non-text chart
  graphics only (it is 4.4:1 on `surface-1`).
- Alarm state always has a marker and a word (`StatusBadge`). `--ch4-*` colours are not used for alarms.
- No view calls `formatRate` and no view reads `keyframes[].sources`; the Task 4 panels show no leak
  rate. A later task that shows a rate must add the rate-interval component (R1-R4:
  `p05–p95 kg/h (median p50)`, 2 significant figures, `model estimate`) first. Two tests pin this:
  `src/app/viewGuards.test.ts` (source scan for `formatRate`, `keyframes`, `rate_kg_h`,
  `anchor_id` in `features/` and `app/`) and `src/app/simulationTruth.test.tsx` (renders every data
  view with the real S1 file and a distinctive-rate fixture; no DOM text or attribute holds a source
  rate or anchor id, and no `kg/h`).

### Keyboard map

Mounted once by `usePlaybackKeys()` on `window`. Ignored inside `input`, `select`, `textarea`,
`[contenteditable]` and with Ctrl, Alt or Meta held.

| Key | Action |
|---|---|
| `Space` | Play or pause (prevents page scroll). Not handled when a button has focus: the button activates itself |
| `ArrowLeft` / `ArrowRight` | Seek -60 s / +60 s; with `Shift` -600 s / +600 s |

### Chart rules

- uPlot 1.6.32 (`uplot`, pinned). `UPlotChart` is a thin wrapper: it imports uPlot on first use
  (`import("uplot")` in the effect; uPlot reads `matchMedia` at load, which jsdom lacks, and the
  dynamic import keeps it out of the entry chunk), builds the instance in `useEffect`, rebuilds it
  only when the memoised `options` change, calls `setData(data, false)` + `redraw()` for new data,
  resizes with a `ResizeObserver`, destroys on unmount. `role="img"` with `ariaLabel`.
- History only: `chartData.ts` sets every value after the current sample to `null`
  (`methaneData`, `windData`); the x axis (elapsed seconds, labelled `+HH:MM`, caption `x axis:
  elapsed time`) covers the whole scenario.
- Methane: one line per `scenario.sensors` id, linear y axis from 0. The selected sensor (if it is
  a methane sensor) and every sensor with a visible alarm are `--accent` 1.5 px and drawn last
  (`highlightLast`); all others `--text-3` 1 px. Legend off; the panel header lists the highlighted
  ids. Wind: speed (m/s, left axis, `--text-2` line) and direction (degrees, right axis 0 to 360,
  points only, `--text-3`; a wind from the north shows points near both 0 and 360).
- Cursor: a 1 px `--focus` vertical line at the current sample, drawn in a `hooks.draw` plugin
  (`cursorPlugin.ts`), repainted with every redraw (once per simulated minute).
- Colours are read once at mount from the CSS variables by `chartTheme.ts` (`getComputedStyle`),
  never typed as hex in TypeScript.
- Docs checked on 2026-11-15 (Context7): uPlot 1.6.32 (`scales.x.time`, `series`, `axes`,
  `hooks.draw`, `setData(data, resetScales)`, `setSize`, `destroy`; the type declarations in
  `node_modules/uplot` confirm `Axis.incrs/splits/values`, `Scale.Range`, `Series.paths`), React
  19.3.1 (effect cleanup, refs), Zustand v5.0.14 listed (repo pins 5.1.0; primitive selectors),
  Tailwind (arbitrary `min-[1280px]:` variant and `grid-cols-[...]`; the repo pins 4.3.5).

### Evidence

`docs/evidence/2026-11-phase-4-panels.png`: S1 at +02:20 (alarm AT-101 closed at 02:20:00 UTC),
1440x900. `docs/evidence/2026-11-phase-4-panels-backend-down.png`: backend stopped, the
`Backend not reachable` state with the start command.

## Anti-slop gate

Every UI task runs `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src`,
which must print `no slop found`, and records a screenshot critique in `docs/WORK_LOG.md`.
Rules: `.ux-profile.md` and `.claude/skills/frontend-design/references/anti-slop.md`.

## Tests

Vitest with the `jsdom` environment and Testing Library. Setup: `src/shared/testing/setup.ts`.
Tests live beside the code as `*.test.ts(x)`. `src/app/vercelConfig.test.ts` reads `vercel.json`
and pins the security headers and the SPA rewrite.

## Type contract

The Pydantic models in `app/backend/plumetrace/facility/` are the source of truth. The frontend
never hand-copies a type or the facility data; it uses three generated files:

| File | Produced by |
|---|---|
| `src/shared/types/generated/contract.schema.json` | `scripts/export_contract.py` (`Contract`: `facility`, `replay_scenario`, `replay_index`) |
| `src/shared/types/generated/contract.ts` | `npm run gen:types` (from the schema) |
| `src/shared/facility/ks07.json` | `scripts/export_contract.py` (`load_facility()` as JSON) |

Regenerate, in this order:

```
cd app && uv run python ../scripts/export_contract.py
cd frontend && npm run gen:types
```

Never edit the generated files by hand; change the Pydantic model or `ks07.yaml` and regenerate.
Output is deterministic: UTF-8, LF line endings, sorted keys, trailing newline (bytes are written,
so Windows does not add CRLF; `.gitattributes` also forces LF). The generated folder is excluded
from ESLint. Drift check: `python scripts/ci_local.py --full`, stage `contract-drift` (Task 8),
re-runs both commands and fails if `git diff` is not empty.

Fixed-length tuples (for example a position `[x, y, z]`) reach the schema as JSON Schema 2020-12
`prefixItems`, which json-schema-to-typescript 16.0.0 ignores and types as `unknown`.
`scripts/export_contract.py` therefore rewrites every `prefixItems` to the draft-07 `items` array
(with `minItems` and `maxItems`), so the generated type is `[number, number, number]`. A node that
has both keywords is an error. `app/backend/tests/test_contract_types.py` checks the rewrite, the
schema and the committed `contract.ts`.
