# Phase 4 · Task 4 — Control-room panels: top bar, alarms, station log, trends, playback

**Skills:** `plan-execution`, `frontend-structure`, `frontend-design` (+ `references/control-room-workspace.md`, `anti-slop.md`), `shadcn`, `dataviz`, `impeccable`, `project-documentation`. Read `.ux-profile.md`.
**Docs to check first (Context7 / official):** uPlot 1.6.32 (options, `series`, `axes`, `hooks.draw`, `setData`, `setSize`, `destroy`), lucide-react 1.72.0 icon names used below.

**Goal:** the working surfaces around the 3D view, driven only by the data layer and the clock.
Every number shown comes from the loaded scenario; nothing is hard-coded.

## Fixed layout (`src/app/AppShell.tsx`, CSS grid, desktop ≥ 1280 px)
```text
┌──────────────────────────── TopBar 48px ─────────────────────────────┐
├──────────── 320px ───────┬──────────── 1fr ────────────┬── 360px ─────┤
│ Alarms (AlarmList)       │ Station view (<main>)        │ Station log  │
│                          │ (3D arrives in Tasks 8–9)    │ (Phase 5:    │
│                          │                              │  + Agent tab)│
├──────────────────────────┴──────────────────────────────┴──────────────┤
│ Trends 220px: Methane (ppm) | Wind (m/s, °)                             │
├──────────────────────────── PlaybackBar 44px ───────────────────────────┤
```
Grid: `grid-rows-[48px_minmax(0,1fr)_220px_44px]`, middle row `grid-cols-[320px_minmax(0,1fr)_360px]`; panels separated by 1 px `border-border-1`, no gaps, no shadows. Below 1280 px wide the right column collapses under the left (Task 10 handles phones).

## Files (under `app/frontend/` unless noted)
| Action | Path |
|---|---|
| Modify | `package.json` → dependency `"uplot": "1.6.32"`; `src/app/AppShell.tsx`, `src/app/AppShell.test.tsx` |
| Create (app) | `src/app/TopBar.tsx`, `src/app/WindReadout.tsx`, `src/app/WindReadout.test.tsx` |
| Create (shared) | `src/shared/data/useCurrentConditions.ts` (export via `shared/data/index.ts`) |
| Create (scenarios) | `src/features/scenarios/index.ts`, `components/ScenarioPicker.tsx`, `components/ScenarioStatus.tsx`, `components/ScenarioStatus.test.tsx`, `components/PlaybackBar.tsx`, `components/PlaybackBar.test.tsx`, `hooks/useScenarioBootstrap.ts`, `hooks/usePlaybackKeys.ts` |
| Create (alarms) | `src/features/alarms/index.ts`, `visibleEvents.ts`, `visibleEvents.test.ts`, `components/AlarmList.tsx`, `components/AlarmRow.tsx`, `components/AlarmList.test.tsx`, `components/StationLog.tsx` |
| Create (trends) | `src/features/trends/index.ts`, `chartData.ts`, `chartData.test.ts`, `chartTheme.ts`, `components/UPlotChart.tsx`, `components/TrendsPanel.tsx` |

## Behaviour and copy (exact strings)
**TopBar** (left → right): `PlumeTrace` (`text-md font-semibold`) · `Station KS-07` (`text-text-2`) · `ScenarioPicker` · mode label · spacer · `WindReadout` · UTC clock (`formatUtc`, mono) · `Simulated` label (bordered, always visible).
- Mode label: live → `Live · local backend`; replay → `Replay`. (Phase 7 changes the replay text.)

**ScenarioPicker**: native `<select aria-label="Scenario">` styled with tokens (`bg-surface-2 border-border-2 text-sm`), one `<option value={id}>{title}</option>` per index entry. Changing it calls `selectScenario(source, id)` and writes `?scenario=<id>` with `history.replaceState`.

**useScenarioBootstrap()** (called once in `AppShell`): `getDataSource()` → `loadIndex` → select the id from `?scenario=` if it is in the index, otherwise `s1_rod_packing` if present, otherwise the first entry.

**ScenarioStatus** (rendered inside the station area, centred, only when not `ready`):
- `loading` → `Loading scenario…` (text only, no spinner animation).
- `error` + `unreachable` + live → heading `Backend not reachable`, body `Start it from the app folder:`, a mono block `uv run uvicorn plumetrace.api.main:app --host 127.0.0.1 --port 8000`, and a `Retry` button (re-runs the selection).
- `error` + `unreachable` + replay → `Replay files could not be loaded.` + `Retry`.
- `error` + `not_found` → `Scenario not found.`
- `error` + `invalid` → `Scenario file is invalid. Regenerate it with scripts/export_scenarios.py.`

**WindReadout**: from `useCurrentConditions()` → `Wind 3.5 m/s from WSW (250°) · Stability D` (speed 1 decimal, direction rounded to whole degrees, `compass16`). With no scenario: `Wind —`.

**useCurrentConditions()**: `{ windSpeed_m_s, windFrom_deg, stability } | null` at `useSampleIndex()` of the active scenario.

**Alarms panel** (`Panel title="Alarms"`): `visibleEvents(scenario, tSeconds)` newest first. Each `AlarmRow` (one `<li>`, 2 lines, `text-sm`):
- line 1: `StatusBadge tone="med"` with text `Methane rise` · sensor id (mono) · time `formatUtc(sim_start_utc, window_start_s + 600)`;
- line 2 (`text-text-2`): `10-min mean 8.4 ppm · baseline 2.1 ppm · downwind of site` (or `· not downwind of site`), values via `formatPpm`.
- Clicking a row → `select(sensor_id)` (selection store) and `seek(window_start_s + 600)`; selected row has `bg-surface-3` and `aria-current="true"`.
- Empty: `No alarms in this period.` (`text-text-3`).
- The `<ul>` has `aria-live="polite"` and `aria-label="Alarm list"`.
- Priority note: all detection events are "Methane rise", tone `med`. Real priorities arrive with triage in Phase 5.

**visibleEvents.ts**: `EVENT_WINDOW_S = 600` (matches backend `WINDOW_S`); `visibleEvents(scenario: ReplayScenario | null, tSeconds: number): ReplayEvent[]` → events with `window_start_s + EVENT_WINDOW_S <= tSeconds`, sorted by `window_start_s` descending, ties by `sensor_id` ascending.

**StationLog** (`Panel title="Station log"`): `scenario.log` entries with `t_s <= tSeconds`, newest first; each row: `formatUtc` (mono) · kind label (`permit` → `Permit`, `gauging` → `Gauging`, `maintenance` → `Maintenance`, `shift_note` → `Shift note`, `calibration` → `Calibration`) · tag (mono, when present) · text. Empty: `No log entries yet.`

**Trends** (`Panel title="Trends"`, two charts side by side, equal width):
- `Methane (ppm)` — one line per methane sensor (`scenario.sensors`). Colours: the selected sensor and every sensor with a visible event use `--accent` 1.5 px; all others `--text-3` 1 px. Log-free linear y axis starting at 0. Legend off; the panel header lists highlighted sensor ids instead.
- `Wind` — speed (m/s, left axis, `--text-2` line) and direction (°, right axis 0–360, points only, `--text-3`).
- Values after the current sample are `null` (the chart shows history only, like a real trend display).
- A vertical cursor line at the current time (`--focus`, 1 px) drawn in a `hooks.draw` plugin.
- Colours are read from CSS variables at mount by `chartTheme.ts` (`getComputedStyle(document.documentElement)`), never typed as hex in TS.

**chartData.ts**:
- `methaneData(scenario: ReplayScenario, sampleIndex: number): { x: number[]; series: (number | null)[][]; ids: string[] }` — `x[i] = i·step_s` (seconds from start), one series per `scenario.sensors` id, entries with `i > sampleIndex` set to `null`.
- `windData(scenario, sampleIndex): { x: number[]; speed: (number | null)[]; fromDeg: (number | null)[] }` — same rule.
- `highlightedSensors(scenario, tSeconds, selectedTag): string[]` — selected tag (if it is a methane sensor) ∪ sensors of `visibleEvents`, sorted.

**UPlotChart**: thin wrapper — creates the `uPlot` instance in `useEffect` on a `div` ref, `ResizeObserver` → `setSize`, new data → `setData(data, false)` + `redraw()`, destroys on unmount; `import "uplot/dist/uPlot.min.css"`. Props: `options` (memoised by the parent), `data`, `ariaLabel` (set on the wrapper `div` with `role="img"`). No chart logic inside.

**PlaybackBar** (full width, `bg-surface-1`):
- Play/Pause button (`lucide-react` `Play` / `Pause`, 16 px) with `aria-label` `Play` / `Pause`.
- Speed buttons `1×`, `10×`, `60×`, `120×` as a `role="radiogroup" aria-label="Playback speed"` (each `role="radio"`, `aria-checked`).
- Scrubber `<input type="range" aria-label="Simulation time" min=0 max=durationS step=60>`; event ticks: a 4 px `--alarm-med` mark under the track at each `window_start_s + 600` (absolutely positioned spans, `aria-hidden`).
- Time readout (mono): `+02:01 · 08:01:00 UTC`.
- Disabled (all controls) while the scenario is not `ready`.

**usePlaybackKeys()** (mounted once in `AppShell`): on `keydown` on `window`, ignored when the target is an `input`, `select`, `textarea` or `[contenteditable]`: `Space` → toggle play (prevent page scroll); `ArrowLeft` / `ArrowRight` → seek −60 / +60 s (`Shift` → ±600 s). Listener removed on unmount.

## Tests (full code)
`src/features/alarms/visibleEvents.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { visibleEvents } from "./visibleEvents";

const ev = (sensor_id: string, window_start_s: number) => ({
  sensor_id,
  window_index: window_start_s / 600,
  window_start_s,
  mean_ppm: 8.4,
  baseline_ppm: 2.1,
  downwind_of_site: true,
});

describe("visibleEvents", () => {
  const s = makeReplay({ events: [ev("AT-104", 600), ev("AT-102", 1200), ev("AT-101", 1200)] });
  it("shows an event only once its 10-minute window has closed", () => {
    expect(visibleEvents(s, 1199)).toHaveLength(1);
    expect(visibleEvents(s, 1800).map((e) => e.sensor_id)).toEqual(["AT-101", "AT-102", "AT-104"]);
  });
  it("handles no scenario", () => {
    expect(visibleEvents(null, 1e9)).toEqual([]);
  });
});
```

`src/features/trends/chartData.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { highlightedSensors, methaneData, windData } from "./chartData";

describe("chartData", () => {
  const s = makeReplay();
  it("hides values after the current sample", () => {
    const d = methaneData(s, 3);
    expect(d.ids).toEqual(["AT-101"]);
    expect(d.x.slice(0, 3)).toEqual([0, 60, 120]);
    expect(d.series[0]?.[3]).toBeCloseTo(2.3);
    expect(d.series[0]?.[4]).toBeNull();
    expect(windData(s, 0).speed.slice(0, 2)).toEqual([3.5, null]);
  });
  it("highlights the selected methane sensor only", () => {
    expect(highlightedSensors(s, 0, "AT-101")).toEqual(["AT-101"]);
    expect(highlightedSensors(s, 0, "K-202")).toEqual([]);
  });
});
```

`src/features/scenarios/components/ScenarioStatus.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataSourceError } from "@/shared/data";

import { ScenarioStatus } from "./ScenarioStatus";

describe("ScenarioStatus", () => {
  it("tells the developer how to start the backend", () => {
    render(
      <ScenarioStatus
        mode="live"
        status="error"
        error={new DataSourceError("unreachable", "down")}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByRole("heading", { name: "Backend not reachable" })).toBeInTheDocument();
    expect(screen.getByText(/uv run uvicorn plumetrace\.api\.main:app/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
  it("renders nothing when ready", () => {
    const { container } = render(
      <ScenarioStatus mode="live" status="ready" error={null} onRetry={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
```
(`ScenarioStatus` is a presentational component: props `mode`, `status`, `error`, `onRetry`. A small container in `AppShell` passes store values.)

`src/features/scenarios/components/PlaybackBar.test.tsx`:
```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";

import { PlaybackBar } from "./PlaybackBar";

describe("PlaybackBar", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(21600);
  });
  it("toggles play and pause", () => {
    render(<PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    expect(useClockStore.getState().playing).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("changes speed through the radio group", () => {
    render(<PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    fireEvent.click(screen.getByRole("radio", { name: "120×" }));
    expect(useClockStore.getState().speed).toBe(120);
  });
  it("is disabled while the scenario is not ready", () => {
    render(<PlaybackBar ready={false} simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    expect(screen.getByRole("button", { name: "Play" })).toBeDisabled();
    expect(screen.getByRole("slider", { name: "Simulation time" })).toBeDisabled();
  });
});
```

`src/features/alarms/components/AlarmList.test.tsx`:
```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import { makeReplay } from "@/shared/testing/replayFixture";

import { AlarmList } from "./AlarmList";

const scenario = makeReplay({
  events: [{ sensor_id: "AT-104", window_index: 1, window_start_s: 60, mean_ppm: 8.4, baseline_ppm: 2.1, downwind_of_site: true }],
});

describe("AlarmList", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useSelectionStore.setState(useSelectionStore.getInitialState());
    useClockStore.getState().reset(1200);
  });
  it("shows the empty state before the event window closes", () => {
    render(<AlarmList scenario={scenario} />);
    expect(screen.getByText("No alarms in this period.")).toBeInTheDocument();
  });
  it("lists a closed event with its numbers and selects the sensor on click", () => {
    useClockStore.getState().seek(660);
    render(<AlarmList scenario={scenario} />);
    expect(screen.getByText("10-min mean 8.4 ppm · baseline 2.1 ppm · downwind of site")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /AT-104/ }));
    expect(useSelectionStore.getState().selectedTag).toBe("AT-104");
  });
});
```
(The row's clickable element is a `<button>` filling the `<li>`; its accessible name includes the sensor id.)

`src/app/WindReadout.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WindReadout } from "./WindReadout";

describe("WindReadout", () => {
  it("formats speed, compass point, degrees and stability", () => {
    render(<WindReadout conditions={{ windSpeed_m_s: 3.46, windFrom_deg: 250.4, stability: "D" }} />);
    expect(screen.getByText("Wind 3.5 m/s from WSW (250°) · Stability D")).toBeInTheDocument();
  });
  it("shows a dash without data", () => {
    render(<WindReadout conditions={null} />);
    expect(screen.getByText("Wind —")).toBeInTheDocument();
  });
});
```

Update `src/app/AppShell.test.tsx` so it stubs `fetch` (`vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("x")))`) and asserts: the `Simulated` label, the regions `Alarms`, `Station log`, `Trends` (by `getByRole("region", { name })`), and the `Station view` main landmark.

## Steps
- [x] Add `uplot` (exact). Write the tests → FAIL → implement in this order: `useCurrentConditions`, alarms, trends data, scenario status/picker/bootstrap, playback bar + keys, top bar, AppShell grid, `UPlotChart`, `TrendsPanel`.
- [x] `npm run lint && npm run typecheck && npm run test && npm run build`; `npm run build:replay && npm run check:replay-bundle`.
- [x] Browser check (Playwright CLI skill): backend running + `npm run dev`, 1440×900. Load S1, play at 120×, check: alarms appear only after their window closes; clicking an alarm seeks and highlights the trend line; scrubber ticks line up with alarms; Space / arrows work; switching to S5 mid-play resets the clock and the old alarms disappear. Stop the backend, reload → `Backend not reachable` with the command; start it, `Retry` recovers.
- [x] Screenshot (S1 at +02:20, 1440×900) → `docs/evidence/2026-11-phase-4-panels.png`. Run `check_slop.py` → `no slop found`; run the `impeccable` critique (hierarchy, density, alignment, numbers, copy) and fix every "must" finding; record findings + fixes in the work log.
- [x] Repo checks (structure — each file ≤ 250 lines; secrets; env).
- [x] **Docs.** FRONTEND.md → "Layout and panels": the grid, each panel's data source, copy rules, the keyboard map, chart rules (history only, cursor, highlight colours). Work-log; `STATUS.md` (last 4.4, next 4.5).
- [ ] **Commit** `feat(frontend): add top bar, alarms, station log, trends and playback`.
