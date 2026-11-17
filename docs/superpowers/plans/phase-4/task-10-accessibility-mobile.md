# Phase 4 · Task 10 — Equipment list, WebGL fallback, reduced motion, keyboard, mobile page

**Skills:** `plan-execution`, `frontend-3d` (rule 9), `frontend-design` (+ `control-room-workspace.md` → accessibility), `shadcn` (tabs), `web-design-guidelines`, `project-documentation`.
**Docs to check first (Context7):** shadcn Tabs (Radix), React 19 error boundaries (class component `componentDidCatch` / `getDerivedStateFromError`), three `WebGLRenderer` context-loss events.

**Goal:** everything the 3D view does is also possible without it: by keyboard, with a screen
reader, without WebGL, with reduced motion, and on a phone (which gets a light page, no 3D).

## Files (under `app/frontend/src/` unless noted)
| Action | Path |
|---|---|
| Create | `features/station3d/EquipmentList.tsx`, `features/station3d/EquipmentList.test.tsx`, `features/station3d/equipmentLabels.ts` (moves the type → English name map out of `TagLabel`; `TagLabel` imports it) |
| Create | `features/station3d/webgl.ts`, `features/station3d/webgl.test.ts`, `features/station3d/StationErrorBoundary.tsx`, `features/station3d/StationFallback.tsx`, `features/station3d/StationView.test.tsx` |
| Modify | `features/station3d/StationView.tsx`, `features/station3d/StationCanvas.tsx` (context-loss listener), `features/station3d/index.ts` (export `EquipmentList`) |
| Create | `app/LeftColumn.tsx` (Tabs: `Alarms` / `Equipment`), `app/SkipLink.tsx`, `app/useViewportClass.ts`, `app/useViewportClass.test.ts`, `app/MobilePage.tsx`, `app/MobilePage.test.tsx` |
| Modify | `app/AppShell.tsx` (left column tabs, skip link, mobile switch) |
| Generated | `app/frontend/public/images/station-fallback.jpg` (from the Task 9 screenshot) |

## Behaviour
**Equipment list** (`Equipment` tab, `Panel title="Equipment"`): every equipment item of `ks07.json` grouped by area in this fixed order — `Inlet` (`PIG-101`, `V-100`), `Compression` (`V-211`–`V-213`, `K-201`–`K-203`, `E-231`–`E-233`, `VS-250`), `Dehydration` (`T-301`, `R-302`), `Fuel gas` (`FG-501`), `Storage` (`TK-401`, `TK-402`, `VRU-410`), `Flare` (`V-602`, `FL-601`), `Metering and outlet` (`M-701`, `PIG-702`), `Buildings` (`CR-901`, `MCC-902`), then `Methane sensors` (`AT-101`–`AT-108`). The area map lives in `equipmentLabels.ts` (`AREA_ORDER`, `AREA_OF_TAG`); a test asserts every spec tag has an area. Each row is a `<button>`: tag (mono) + type name; `aria-pressed` when selected; click / Enter / Space → `select(tag)` (the 3D view highlights and flies there). Selecting in 3D scrolls the row into view (`scrollIntoView({ block: "nearest" })`) and marks it.

**WebGL detection** (`webgl.ts`): `hasWebGL2(): boolean` — creates a canvas, `getContext("webgl2")`, returns `!!ctx`, loses the context (`WEBGL_lose_context`) if available; any exception → `false`. Called once in `StationView`.

**Fallback** (`StationFallback.tsx`): `<figure>` with `<img src="/images/station-fallback.jpg" alt="Station KS-07 seen from the south-west: compressor shelters, vent stack VS-250, tanks and flare." width="1920" height="1080">` scaled to cover, and a caption `3D view unavailable on this device. The alarms, equipment list and trends still work.` Shown when: no WebGL2; `StationErrorBoundary` caught an error (model failed to load, shader compile error); the WebGL context was lost and not restored within 3 s (`webglcontextlost` → start a 3 s timer; `webglcontextrestored` → cancel). Errors are logged once with `console.error`.

**Reduced motion** (already wired in Tasks 8–9): verify and add one test — with `matchMedia` mocked to reduce, `useStationStore.getState().reducedMotion === true`.

**Keyboard and focus**
- `SkipLink`: first focusable element, visually hidden until focused, text `Skip to alarms`, target `#alarms-panel`.
- Tab order: top bar → left column tabs → list → station quality menu → station log → trends (charts are `role="img"` with an `aria-label` summarising the latest values, not focusable) → playback bar.
- Global keys from Task 4 stay; `R` (reset view) is ignored when focus is in a form control.
- Visible focus everywhere (token `--focus`); no `outline: none` without a replacement.

**Viewport classes** (`useViewportClass.ts`): `"mobile"` when `matchMedia("(max-width: 767px)")` matches, or when `(pointer: coarse)` matches **and** width < 1024 px; otherwise `"desktop"`; updates on change.

**Mobile page** (`MobilePage.tsx`, rendered instead of the control room for `"mobile"`; the 3D chunk is never imported): header `PlumeTrace` + `Simulated` label; heading `Methane leak detection for a simulated compressor station`; paragraph `PlumeTrace watches eight fence-line methane sensors at the fictional Station KS-07, detects rises, locates the most likely leaking component with a dispersion model and drafts a work order for an operator to approve.`; the fallback image; text `Open this page in a desktop browser to use the interactive control room.`. The mobile page shows no weather data, so it needs no data attribution. Phase 7 adds the demo video here.

## Tests (full code)
`app/useViewportClass.test.ts`:
```ts
import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useViewportClass } from "./useViewportClass";

function mockMedia(matches: Record<string, boolean>, width: number): void {
  vi.stubGlobal("innerWidth", width);
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: matches[q] ?? false,
    media: q,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("useViewportClass", () => {
  it("treats narrow screens as mobile", () => {
    mockMedia({ "(max-width: 767px)": true }, 390);
    expect(renderHook(() => useViewportClass()).result.current).toBe("mobile");
  });
  it("treats a coarse pointer under 1024 px as mobile", () => {
    mockMedia({ "(pointer: coarse)": true }, 900);
    expect(renderHook(() => useViewportClass()).result.current).toBe("mobile");
  });
  it("keeps large touch screens on desktop", () => {
    mockMedia({ "(pointer: coarse)": true }, 1366);
    expect(renderHook(() => useViewportClass()).result.current).toBe("desktop");
  });
});
```

`features/station3d/webgl.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { hasWebGL2 } from "./webgl";

afterEach(() => vi.restoreAllMocks());

describe("hasWebGL2", () => {
  it("is false when the context cannot be created", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    expect(hasWebGL2()).toBe(false);
  });
  it("is false when getContext throws", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(hasWebGL2()).toBe(false);
  });
});
```

`features/station3d/StationView.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("./webgl", () => ({ hasWebGL2: () => false }));

import { StationView } from "./StationView";

describe("StationView", () => {
  it("shows the static fallback without WebGL2", () => {
    render(<StationView />);
    expect(screen.getByRole("img", { name: /Station KS-07 seen from the south-west/ })).toBeInTheDocument();
    expect(screen.getByText(/3D view unavailable on this device/)).toBeInTheDocument();
  });
});
```

`features/station3d/EquipmentList.test.tsx`:
```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";
import { useSelectionStore } from "@/shared/selection";

import { EquipmentList } from "./EquipmentList";
import { AREA_OF_TAG } from "./equipmentLabels";

describe("EquipmentList", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));
  it("gives every spec tag an area", () => {
    for (const e of facility.equipment) expect(AREA_OF_TAG[e.tag]).toBeDefined();
  });
  it("selects by click and marks the pressed row", () => {
    render(<EquipmentList />);
    const row = screen.getByRole("button", { name: /VS-250/ });
    fireEvent.click(row);
    expect(useSelectionStore.getState().selectedTag).toBe("VS-250");
    expect(row).toHaveAttribute("aria-pressed", "true");
  });
});
```
(Element `scrollIntoView` does not exist in jsdom: add `Element.prototype.scrollIntoView = () => undefined;` to `src/shared/testing/setup.ts` in this task.)

`app/MobilePage.test.tsx`: renders the heading text above, the `Simulated` label, and asserts no element with `aria-label="Station view"` exists.

## Steps
- [x] Tests → FAIL → implement: `equipmentLabels` (+ refactor `TagLabel`), `EquipmentList`, `LeftColumn` tabs (`npx --yes shadcn@4.23.0 add tabs` already done in Task 2 — reuse `src/shared/ui/tabs.tsx`), `webgl`, `StationFallback`, `StationErrorBoundary`, context-loss handling, `SkipLink`, `useViewportClass`, `MobilePage`, AppShell switch.
- [x] Make the fallback image: take a **clean** review-camera screenshot with no scenario plume (load S5 at t = 0, hide overlays with `?clean` — add that dev-only query flag in `StationView`, ignored in production builds) via Playwright at 1920×1080, JPEG quality 80 → `public/images/station-fallback.jpg` (≤ 300 KB).
- [x] `npm run lint && npm run typecheck && npm run test && npm run build && npm run build:replay && npm run check:replay-bundle`.
- [x] Browser checks (Playwright CLI skill): keyboard-only run through every control (record the tab order); Chromium with `--disable-webgl` → fallback; DevTools "lose context" (`WEBGL_lose_context.loseContext()` via the console) → fallback after 3 s; reduced motion; 390×844 and 820×1180 touch emulation → mobile page with **no** request for `ks07.glb` (check the network log).
- [x] `check_slop.py`; `web-design-guidelines` review of the left column, mobile page and fallback; fix every issue; record in the work log. Repo checks.
- [ ] **Docs.** FRONTEND.md → "Accessibility and fallbacks" (equipment list, areas, keyboard map + tab order, WebGL detection and fallback triggers, reduced motion, viewport classes, mobile page). Work-log; `STATUS.md` (last 4.10, next 4.11).
- [ ] **Commit** `feat(frontend): add equipment list, WebGL fallback, keyboard access and mobile page`.
