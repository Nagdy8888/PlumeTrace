# Phase 4 · Task 3 — Data layer: DataSource, ReplaySource, LiveSource, playback clock, stores

**Skills:** `plan-execution`, `frontend-structure`, `fastapi` (only for the shape check), `project-documentation`.
**Docs to check first (Context7):** Zustand 5.1.0 (`create`, selectors, `getState`, `subscribe`), Vite 8 (`import.meta.env.MODE`, `--mode`, dynamic `import()` code splitting).

**Goal:** every feature gets scenario data through one interface. The public build contains only
the replay implementation; the local build talks to FastAPI. A playback clock drives everything;
switching scenarios never mixes old and new data.

## Fixed decisions
- `DataSource` lives in `src/shared/data/`. Two implementations: `ReplaySource` (static files under `/replay/`) and `LiveSource` (`/api/...`). Chosen once by `getDataSource()` from `import.meta.env.MODE`.
- Replay files are copied from `app/replay/` to `app/frontend/public/replay/` by `npm run copy:replay` (runs automatically before `dev`, `build` and `build:replay`). `public/replay/` is git-ignored.
- Without the backend you can still run the UI locally: `npm run dev -- --mode replay`.
- Stores: `shared/data/scenarioStore.ts` (which scenario, load status, loaded data), `shared/playback/clockStore.ts` (simulation time), `shared/selection/selectionStore.ts` (selected / hovered equipment tag). They are business-neutral containers; features read them through hooks.
- The clock is the single time source. Panels re-render once per 60 s sample (selector on the sample index), never per animation frame. The 3D layer reads `useClockStore.getState()` inside `useFrame`.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/plumetrace/simulator/replay_schema.py` (add `ReplayIndexEntry`, `ReplayIndex`), `app/backend/plumetrace/simulator/export.py` (add `build_index`), `scripts/export_scenarios.py` (also writes `index.json`), `scripts/export_contract.py` (`Contract` gains `replay_index: ReplayIndex`) |
| Modify | `app/backend/tests/simulator/test_export.py` (add 1 test), `app/backend/tests/test_export_contract.py` (assertion), `app/backend/tests/api/test_api.py` (add 1 test) |
| Generated | `app/replay/scenarios/index.json`; regenerated `contract.schema.json`, `contract.ts` |
| Check | `.gitignore` already contains `app/frontend/public/replay/` (added by the planner) |
| Modify (frontend) | `package.json` (dependency `"zustand": "5.1.0"`; scripts below) |
| Create (frontend `src/shared/`) | `data/DataSource.ts`, `data/errors.ts`, `data/fetchJson.ts`, `data/validateReplay.ts`, `data/ReplaySource.ts`, `data/LiveSource.ts`, `data/getDataSource.ts`, `data/scenarioStore.ts`, `data/index.ts`, `playback/clockStore.ts`, `playback/usePlaybackLoop.ts`, `playback/index.ts`, `selection/selectionStore.ts`, `selection/index.ts`, `testing/replayFixture.ts` |
| Create (tests) | `data/validateReplay.test.ts`, `data/ReplaySource.test.ts`, `data/LiveSource.test.ts`, `data/scenarioStore.test.ts`, `playback/clockStore.test.ts` |

## Backend additions
`replay_schema.py` (same `extra="forbid"` config as the other models):
- `class ReplayIndexEntry(BaseModel): id: str; title: str; duration_h: int; is_mvp: bool`
- `class ReplayIndex(BaseModel): schema_version: Literal[1]; scenarios: list[ReplayIndexEntry]`

`export.py`:
- `def build_index(definitions: Iterable[ScenarioDefinition]) -> ReplayIndex` — one entry per definition, sorted by `id`, `is_mvp=True` (every registered scenario is MVP in this phase).
- `def index_bytes(index: ReplayIndex) -> bytes` — same serialisation as `replay_bytes` (sorted keys, compact separators, UTF-8, trailing `\n`), no size check.

`scripts/export_scenarios.py` → after the per-scenario files, write `app/replay/scenarios/index.json` with `index_bytes(build_index(SCENARIOS.values()))` and print `index.json: <n> bytes`.

`scripts/export_contract.py` → `class Contract(BaseModel): facility: FacilitySpec; replay_scenario: ReplayScenario; replay_index: ReplayIndex`. In `test_export_contract.py` the assertion becomes `assert {"facility", "replay_scenario", "replay_index"} <= set(schema["properties"])`.

Add to `app/backend/tests/simulator/test_export.py`:
```python
def test_index_lists_registered_scenarios_sorted() -> None:
    """index.json lists the three MVP scenarios, sorted by id."""
    from plumetrace.simulator.export import build_index
    from plumetrace.simulator.scenarios import SCENARIOS

    index = build_index(SCENARIOS.values())
    assert index.schema_version == 1
    assert [e.id for e in index.scenarios] == ["s1_rod_packing", "s4_planned_blowdown",
                                               "s5_sensor_drift"]
    assert [e.duration_h for e in index.scenarios] == [6, 4, 6]
```

Add to `app/backend/tests/api/test_api.py`:
```python
def test_scenario_summary_matches_replay_index_entry() -> None:
    """Live and replay scenario lists share one shape, so the frontend uses one type."""
    from plumetrace.api.schemas import ScenarioSummary
    from plumetrace.simulator.replay_schema import ReplayIndexEntry

    assert ScenarioSummary.model_json_schema()["properties"] == \
        ReplayIndexEntry.model_json_schema()["properties"]
```

## Frontend `package.json` scripts (add exactly)
```json
"copy:replay": "node -e \"const fs=require('node:fs');fs.rmSync('public/replay',{recursive:true,force:true});fs.cpSync('../replay','public/replay',{recursive:true});console.log('replay files copied')\"",
"predev": "npm run copy:replay",
"prebuild": "npm run copy:replay",
"build:replay": "npm run copy:replay && tsc --noEmit -p tsconfig.json && vite build --mode replay",
"check:replay-bundle": "node -e \"const fs=require('node:fs');const p=require('node:path');const d='dist/assets';const bad=fs.readdirSync(d).filter(f=>f.endsWith('.js')&&fs.readFileSync(p.join(d,f),'utf8').includes('/api/'));if(bad.length){console.error('live API code in replay bundle: '+bad.join(', '));process.exit(1)}console.log('replay bundle OK')\""
```
(`node -e` runs as CommonJS even though the package is `"type": "module"`, so `require` works.)

## Interfaces (frontend; TSDoc on every export)
Types come from `@/shared/types/generated/contract` (`ReplayScenario`, `ReplayIndex`, `ReplayIndexEntry`). Never redeclare them.

`data/DataSource.ts`:
```ts
import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

/** Where scenario data comes from: the local backend or static replay files. */
export type DataSourceMode = "live" | "replay";

/** The one interface every feature uses to get scenario data. Phase 5 adds agent runs. */
export interface DataSource {
  readonly mode: DataSourceMode;
  /** List the available scenarios, sorted by id. */
  listScenarios(signal?: AbortSignal): Promise<ReplayIndexEntry[]>;
  /** Load one scenario's full time series. */
  loadScenario(id: string, signal?: AbortSignal): Promise<ReplayScenario>;
}
```

`data/errors.ts`:
```ts
/** Why a data request failed: no server, unknown id, or a malformed file. */
export type DataSourceErrorKind = "unreachable" | "not_found" | "invalid";

/** Error raised by every DataSource method. The UI chooses its message from `kind`. */
export class DataSourceError extends Error {
  readonly kind: DataSourceErrorKind;

  /**
   * @param kind - Failure category.
   * @param message - Developer-facing detail (never shown verbatim to visitors).
   */
  constructor(kind: DataSourceErrorKind, message: string) {
    super(message);
    this.name = "DataSourceError";
    this.kind = kind;
  }
}
```

`data/fetchJson.ts` — `export async function fetchJson(url: string, signal?: AbortSignal): Promise<unknown>`:
- `fetch(url, { signal, headers: { Accept: "application/json" } })`; a rejected fetch that is an `AbortError` is re-thrown unchanged; any other rejection → `DataSourceError("unreachable", …)`.
- `404` → `DataSourceError("not_found", …)`; any other non-OK status → `"unreachable"` (the Vite proxy answers 5xx when the backend is down).
- Body not JSON → `"invalid"`.

`data/validateReplay.ts`:
- `export function parseReplayScenario(data: unknown, expectedId: string): ReplayScenario` — throws `DataSourceError("invalid", …)` unless: `data` is an object; `schema_version === 1`; `simulated === true`; `scenario_id === expectedId`; `step_s > 0`; with `n = Math.round(duration_s / step_s)`: `wind_speed_m_s`, `wind_from_deg`, `stability` and every array in `series` have length `n`; every `series` key has a `units` entry.
- `export function parseReplayIndex(data: unknown): ReplayIndexEntry[]` — accepts either a `ReplayIndex` object (`schema_version === 1`, `scenarios` array) **or** a bare array (the live API returns `list[ScenarioSummary]`); each entry must have string `id`, string `title`, number `duration_h`, boolean `is_mvp`; returns the entries sorted by `id`.

`data/ReplaySource.ts` — `export class ReplaySource implements DataSource` with `mode = "replay"`; `listScenarios` → `parseReplayIndex(await fetchJson("/replay/scenarios/index.json", signal))`; `loadScenario(id)` → id must match `/^s[0-9]+_[a-z0-9_]+$/` (else `DataSourceError("not_found")` without fetching) → `parseReplayScenario(await fetchJson(\`/replay/scenarios/${id}.json\`, signal), id)`.

`data/LiveSource.ts` — `export class LiveSource implements DataSource` with `mode = "live"`; `listScenarios` → `parseReplayIndex(await fetchJson("/api/scenarios", signal))`; `loadScenario(id)` → same id check → `parseReplayScenario(await fetchJson(\`/api/scenarios/${encodeURIComponent(id)}/replay\`, signal), id)`.

`data/getDataSource.ts`:
```ts
import type { DataSource } from "./DataSource";

let cached: Promise<DataSource> | null = null;

/**
 * Return the data source for this build. `vite build --mode replay` replaces
 * `import.meta.env.MODE` with "replay", so the live branch and its module are removed
 * from the public bundle (checked by `npm run check:replay-bundle`).
 *
 * @returns The memoised data source.
 */
export function getDataSource(): Promise<DataSource> {
  if (cached === null) {
    cached =
      import.meta.env.MODE === "replay"
        ? import("./ReplaySource").then((m) => new m.ReplaySource())
        : import("./LiveSource").then((m) => new m.LiveSource());
  }
  return cached;
}

/** Test hook: forget the memoised source. */
export function resetDataSourceForTests(): void {
  cached = null;
}
```

`data/scenarioStore.ts` (Zustand `create`):
- State: `index: ReplayIndexEntry[]`, `indexStatus: "idle" | "loading" | "ready" | "error"`, `activeId: string | null`, `scenario: ReplayScenario | null`, `status: "idle" | "loading" | "ready" | "error"`, `error: DataSourceError | null`, `requestSeq: number`.
- `loadIndex(source: DataSource): Promise<void>` — sets loading → ready / error.
- `selectScenario(source: DataSource, id: string): Promise<void>`:
  1. abort the previous request's `AbortController` (module-level variable), create a new one;
  2. `seq = requestSeq + 1`; set `{ activeId: id, scenario: null, status: "loading", error: null, requestSeq: seq }`; call `useClockStore.getState().reset(0)`;
  3. await `source.loadScenario(id, controller.signal)`;
  4. **only if `get().requestSeq === seq`**: set `{ scenario, status: "ready" }` and `useClockStore.getState().reset(scenario.duration_s)`; on error (ignore `AbortError`) set `{ status: "error", error }` — again only if the sequence still matches.
- Hooks: `useActiveScenario(): ReplayScenario | null`, `useScenarioStatus()`.

`playback/clockStore.ts`:
- `SPEEDS = [1, 10, 60, 120] as const`; `type Speed = (typeof SPEEDS)[number]`; `DEFAULT_SPEED: Speed = 60`; `SAMPLE_STEP_S = 60`.
- State: `tSeconds: number`, `durationS: number`, `playing: boolean`, `speed: Speed`.
- Actions: `play()` (no-op when `durationS === 0`; when at the end, restarts from 0), `pause()`, `setSpeed(s)`, `seek(t)` (clamp to `[0, durationS]`), `reset(durationS)` (`t = 0`, `playing = false`, speed unchanged), `tick(dtRealS)` (when playing: `t = min(durationS, t + dtRealS·speed)`; reaching the end sets `playing = false`; ignores `dtRealS` ≤ 0 or > 1 — a tab that slept must not jump).
- `useSampleIndex(): number` — selector `Math.max(0, Math.min(n − 1, Math.floor(t / SAMPLE_STEP_S)))` with `n = max(1, round(durationS / SAMPLE_STEP_S))`; returns a number so React re-renders only when the index changes.

`playback/usePlaybackLoop.ts` — `usePlaybackLoop(): void`: one `requestAnimationFrame` loop mounted once in `AppShell`; computes `dt` from the rAF timestamp, calls `tick(dt / 1000)`; cancels on unmount. No React state.

`selection/selectionStore.ts` — state `selectedTag: string | null`, `hoveredTag: string | null`; actions `select(tag | null)`, `hover(tag | null)`; selecting the already-selected tag clears it.

Each folder's `index.ts` re-exports its public API only (features import `@/shared/data`, `@/shared/playback`, `@/shared/selection`, never inner files).

## Test fixture — `src/shared/testing/replayFixture.ts`
```ts
import type { ReplayScenario } from "@/shared/types/generated/contract";

/**
 * Build a small valid replay scenario (10 one-minute samples) for tests.
 *
 * @param overrides - Fields to replace.
 * @returns A replay scenario that passes `parseReplayScenario`.
 */
export function makeReplay(overrides: Partial<ReplayScenario> = {}): ReplayScenario {
  const n = 10;
  return {
    schema_version: 1,
    scenario_id: "s1_rod_packing",
    title: "Test scenario",
    sim_start_utc: "2025-07-15T06:00:00Z",
    duration_s: n * 60,
    step_s: 60,
    sensors: [{ id: "AT-101", x_m: 10, y_m: 20, z_m: 1.5 }],
    series: { "AT-101": Array.from({ length: n }, (_, i) => 2 + i * 0.1) },
    units: { "AT-101": "ppm" },
    wind_speed_m_s: Array(n).fill(3.5),
    wind_from_deg: Array(n).fill(250),
    stability: Array(n).fill("D"),
    events: [],
    log: [],
    grid: { x0_m: 0, y0_m: 0, dx_m: 5, dy_m: 5, nx: 40, ny: 30, encoding: "log_u8_0.1_1000ppm" },
    keyframes: [],
    attribution: "Weather: Open-Meteo (CC BY 4.0)",
    simulated: true,
    ...overrides,
  };
}
```
If `npm run typecheck` rejects a field name, the generated contract is the truth: regenerate types (`npm run gen:types`) and STOP if the generated names differ from `replay_schema.py` — do not rename fields here.

## Tests (full code)
`src/shared/data/validateReplay.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { DataSourceError } from "./errors";
import { parseReplayIndex, parseReplayScenario } from "./validateReplay";

describe("parseReplayScenario", () => {
  it("accepts a valid file", () => {
    expect(parseReplayScenario(makeReplay(), "s1_rod_packing").scenario_id).toBe("s1_rod_packing");
  });
  it.each([
    ["wrong id", makeReplay({ scenario_id: "s4_planned_blowdown" })],
    ["not simulated", { ...makeReplay(), simulated: false }],
    ["schema version", { ...makeReplay(), schema_version: 2 }],
    ["short series", makeReplay({ series: { "AT-101": [1, 2] } })],
    ["missing unit", makeReplay({ units: {} })],
    ["short wind", makeReplay({ wind_speed_m_s: [1] })],
    ["not an object", "hello"],
  ])("rejects %s", (_label, data) => {
    expect(() => parseReplayScenario(data, "s1_rod_packing")).toThrow(DataSourceError);
  });
});

describe("parseReplayIndex", () => {
  const entries = [
    { id: "s5_sensor_drift", title: "B", duration_h: 6, is_mvp: true },
    { id: "s1_rod_packing", title: "A", duration_h: 6, is_mvp: true },
  ];
  it("accepts the replay index object and sorts by id", () => {
    expect(parseReplayIndex({ schema_version: 1, scenarios: entries }).map((e) => e.id)).toEqual([
      "s1_rod_packing",
      "s5_sensor_drift",
    ]);
  });
  it("accepts the live API array", () => {
    expect(parseReplayIndex(entries)).toHaveLength(2);
  });
  it("rejects malformed entries", () => {
    expect(() => parseReplayIndex([{ id: 3 }])).toThrow(DataSourceError);
  });
});
```

`src/shared/data/ReplaySource.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { ReplaySource } from "./ReplaySource";

function respond(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.unstubAllGlobals());

describe("ReplaySource", () => {
  it("loads a scenario file from /replay", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, makeReplay()));
    vi.stubGlobal("fetch", fetchMock);
    const s = await new ReplaySource().loadScenario("s1_rod_packing");
    expect(s.title).toBe("Test scenario");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/replay/scenarios/s1_rod_packing.json");
  });
  it("rejects ids that are not scenario ids without fetching", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(new ReplaySource().loadScenario("../secrets")).rejects.toMatchObject({ kind: "not_found" });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("maps 404 to not_found", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(404, {})));
    await expect(new ReplaySource().loadScenario("s9_missing")).rejects.toMatchObject({ kind: "not_found" });
  });
});
```

`src/shared/data/LiveSource.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { LiveSource } from "./LiveSource";

afterEach(() => vi.unstubAllGlobals());

describe("LiveSource", () => {
  it("reports an unreachable backend when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(new LiveSource().listScenarios()).rejects.toMatchObject({ kind: "unreachable" });
  });
  it("treats a proxy 502 as unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 502 })));
    await expect(new LiveSource().listScenarios()).rejects.toMatchObject({ kind: "unreachable" });
  });
  it("calls the relative API path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ id: "s1_rod_packing", title: "A", duration_h: 6, is_mvp: true }]), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await new LiveSource().listScenarios();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/scenarios");
  });
});
```

`src/shared/data/scenarioStore.test.ts`:
```ts
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { useScenarioStore } from "./scenarioStore";

function deferred<T>(): { promise: Promise<T>; resolve: (v: T) => void } {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

describe("scenarioStore", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
  });

  it("ignores a slow earlier response after a newer selection", async () => {
    const slow = deferred<ReplayScenario>();
    const fast = deferred<ReplayScenario>();
    const source: DataSource = {
      mode: "replay",
      listScenarios: () => Promise.resolve([]),
      loadScenario: (id) => (id === "s1_rod_packing" ? slow.promise : fast.promise),
    };
    const first = useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    const second = useScenarioStore.getState().selectScenario(source, "s5_sensor_drift");
    fast.resolve(makeReplay({ scenario_id: "s5_sensor_drift", duration_s: 1200, step_s: 60 }));
    await second;
    slow.resolve(makeReplay());
    await first;
    const state = useScenarioStore.getState();
    expect(state.activeId).toBe("s5_sensor_drift");
    expect(state.scenario?.scenario_id).toBe("s5_sensor_drift");
    expect(useClockStore.getState().durationS).toBe(1200);
  });

  it("records a typed error", async () => {
    const { DataSourceError } = await import("./errors");
    const source: DataSource = {
      mode: "live",
      listScenarios: () => Promise.resolve([]),
      loadScenario: () => Promise.reject(new DataSourceError("unreachable", "down")),
    };
    await useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    expect(useScenarioStore.getState().status).toBe("error");
    expect(useScenarioStore.getState().error?.kind).toBe("unreachable");
  });
});
```
(The fixture's `series` arrays have 10 entries; the store does not re-validate, so `duration_s: 1200` here is fine.)

`src/shared/playback/clockStore.test.ts`:
```ts
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "./clockStore";

describe("clockStore", () => {
  beforeEach(() => useClockStore.setState(useClockStore.getInitialState()));

  it("advances by real time times speed and stops at the end", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.setSpeed(60);
    c.play();
    useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(30);
    for (let i = 0; i < 40; i += 1) useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(600);
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("ignores long gaps (sleeping tab) and clamps seeks", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.play();
    useClockStore.getState().tick(5);
    expect(useClockStore.getState().tSeconds).toBe(0);
    useClockStore.getState().seek(9999);
    expect(useClockStore.getState().tSeconds).toBe(600);
  });
  it("does not play an empty timeline", () => {
    useClockStore.getState().play();
    expect(useClockStore.getState().playing).toBe(false);
  });
});
```

## Steps
- [x] Backend: tests → FAIL → implement `ReplayIndexEntry`, `ReplayIndex`, `build_index`, `index_bytes`, script + contract changes → `uv run pytest app/backend -q` green. Run `cd app && uv run python ../scripts/export_scenarios.py` and `uv run python ../scripts/export_contract.py`, then `cd frontend && npm run gen:types`.
- [x] Confirm `.gitignore` contains `app/frontend/public/replay/`.
- [x] Frontend: add `zustand` (exact), scripts; write the tests → FAIL → implement every file above.
- [x] `npm run lint && npm run typecheck && npm run test`, then `npm run build:replay && npm run check:replay-bundle` → must print `replay bundle OK`; then `npm run build` (live build) succeeds.
- [x] Manual: start the backend (Task 1 command) and `npm run dev`; in the browser console `fetch("/api/scenarios").then(r => r.json())` lists three scenarios. Stop the backend and confirm the same call now fails (proves the "unreachable" path is real).
- [x] Repo checks (structure, secrets, env); `check_slop.py` → `no slop found`.
- [x] **Docs.** FRONTEND.md → "Data layer": the interface, both implementations, the error kinds and their meaning, the mode switch and bundle check, the three stores (state + actions), the playback rules (speeds, sample-index re-render rule, 1 s gap guard). REPLAY.md → "index.json". LOCAL_DEVELOPMENT → "Run the UI without the backend" (`npm run dev -- --mode replay`). Work-log; `STATUS.md` (last 4.3, next 4.4).
- [ ] **Commit** `feat(frontend): add data sources, playback clock and scenario store`.
