# Phase 4 · Task 11 — Playwright flows, visual baseline, accessibility scan, fps, phase evidence

**Skills:** `plan-execution`, `playwright-cli`, `frontend-3d` (+ `references/performance-and-testing.md`), `verify-and-review` (phase end), `security-checks` (full gate), `project-documentation`.
**Docs to check first (Context7 / official):** @playwright/test 1.65.0 (`defineConfig`, `projects`, `webServer`, `toHaveScreenshot`, `launchOptions.args`, `reducedMotion`, `devices`), @axe-core/playwright 4.14.0 (`AxeBuilder`, `withTags`).

**Permission:** `npx playwright install chromium` downloads a browser build (~170 MB from
playwright.azureedge.net). Ask the owner in chat before running it; wait for a yes.

## Fixed decisions
- E2E runs against the **replay** build served by `vite preview` (port 4173) — deterministic, no backend.
- Two Playwright projects: `no-webgl` (Chromium with `--disable-webgl --disable-webgl2`; fallback path; runs in `ci_local.py --full`) and `webgl` (local only: real GPU; functional 3D checks, visual baseline, fps).
- Visual baselines are taken on the owner's machine and are **not** compared in `ci_local.py` (GPU output differs; compared only in the manual `webgl` run).
- The fps spec always asserts ≥ 58 fps; it runs only locally via `npm run e2e:fps`.

## Files (under `app/frontend/` unless noted)
| Action | Path |
|---|---|
| Modify | `package.json` → dev `"@playwright/test": "1.65.0"`, `"@axe-core/playwright": "4.14.0"`; scripts below; `eslint.config.js` → include `e2e/**` with the TS rules; `tsconfig.json` → `"include"` adds `"e2e"` and `"playwright.config.ts"` |
| Create | `playwright.config.ts`, `e2e/helpers.ts`, `e2e/control-room.spec.ts`, `e2e/mobile.spec.ts`, `e2e/a11y.spec.ts`, `e2e/station3d.spec.ts`, `e2e/visual.spec.ts`, `e2e/fps.spec.ts` |
| Check | `.gitignore` already contains `app/frontend/test-results/` and `app/frontend/playwright-report/` (added by the planner) |
| Modify | `scripts/ci_local.py` → stages `replay-build` and `e2e`; `app/backend/tests/test_ci_local.py` (one assertion) |
| Create | `docs/evidence/2026-11-phase-4-ui.md` (phase evidence) |

## `package.json` scripts (add exactly)
```json
"e2e": "playwright test --project=no-webgl",
"e2e:local": "playwright test --project=no-webgl --project=webgl",
"e2e:fps": "playwright test --project=webgl e2e/fps.spec.ts",
"e2e:update-baseline": "playwright test --project=webgl e2e/visual.spec.ts --update-snapshots"
```

## `playwright.config.ts` (exact)
```ts
import { defineConfig, devices } from "@playwright/test";

/** Playwright configuration: replay build on vite preview; WebGL and no-WebGL projects. */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000, toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  fullyParallel: false,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:4173", viewport: { width: 1920, height: 1080 }, trace: "retain-on-failure" },
  webServer: {
    command: "npm run build:replay && npx vite preview --mode replay --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 180_000,
  },
  projects: [
    {
      name: "no-webgl",
      testIgnore: ["**/station3d.spec.ts", "**/visual.spec.ts", "**/fps.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 }, launchOptions: { args: ["--disable-webgl", "--disable-webgl2"] } },
    },
    {
      name: "webgl",
      testMatch: ["**/station3d.spec.ts", "**/visual.spec.ts", "**/fps.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 }, launchOptions: { args: ["--ignore-gpu-blocklist", "--enable-gpu"] } },
    },
  ],
});
```

## `e2e/helpers.ts`
- `openScenario(page, id)` → `page.goto(\`/?scenario=${id}\`)`, waits until the playback slider is enabled.
- `seekTo(page, seconds)` → sets the `Simulation time` slider value with `locator.fill(String(seconds))` (range inputs accept `fill`) and waits one animation frame.
- `measureFps(page, ms)` → `page.evaluate` that counts `requestAnimationFrame` callbacks for `ms` and returns `{ avgFps, p95FrameMs }` (sorted frame deltas, 95th percentile).

## Specs (full code)
`e2e/control-room.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

import { openScenario, seekTo } from "./helpers";

test("S1: alarms appear after the release and select a sensor", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await expect(page.getByText("No alarms in this period.")).toBeVisible();
  await seekTo(page, 14_400);
  const alarms = page.getByRole("list", { name: "Alarm list" }).getByRole("button");
  await expect(alarms.first()).toBeVisible();
  await alarms.first().click();
  await expect(alarms.first()).toHaveAttribute("aria-current", "true");
});

test("switching scenarios resets the clock and the alarms", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await seekTo(page, 14_400);
  await page.getByRole("combobox", { name: "Scenario" }).selectOption("s5_sensor_drift");
  await expect(page.getByRole("slider", { name: "Simulation time" })).toHaveValue("0");
  await expect(page.getByText("No alarms in this period.")).toBeVisible();
  await expect(page).toHaveURL(/scenario=s5_sensor_drift/);
});

test("keyboard: space plays and pauses, arrows seek", async ({ page }) => {
  await openScenario(page, "s4_planned_blowdown");
  await page.locator("body").click({ position: { x: 5, y: 5 } });
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();
  await page.keyboard.press("Space");
  await page.keyboard.press("Shift+ArrowRight");
  const v = Number(await page.getByRole("slider", { name: "Simulation time" }).inputValue());
  expect(v).toBeGreaterThanOrEqual(600);
});

test("without WebGL the fallback and equipment list still work", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await expect(page.getByText(/3D view unavailable on this device/)).toBeVisible();
  await page.getByRole("tab", { name: "Equipment" }).click();
  await page.getByRole("button", { name: /VS-250/ }).click();
  await expect(page.getByRole("button", { name: /VS-250/ })).toHaveAttribute("aria-pressed", "true");
});

test("the replay build never calls the live API", async ({ page }) => {
  const apiCalls: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).pathname.startsWith("/api/")) apiCalls.push(r.url());
  });
  await openScenario(page, "s1_rod_packing");
  expect(apiCalls).toEqual([]);
});
```

`e2e/mobile.spec.ts`:
```ts
import { devices, expect, test } from "@playwright/test";

test.use({ ...devices["iPhone 13"], browserName: "chromium" });

test("phones get the light page and never download the 3D model", async ({ page }) => {
  const glb: string[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith(".glb")) glb.push(r.url());
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Methane leak detection for a simulated compressor station" })).toBeVisible();
  await expect(page.getByText("Simulated", { exact: true })).toBeVisible();
  expect(glb).toEqual([]);
});
```
(`devices["iPhone 13"]` defaults to WebKit; `browserName: "chromium"` keeps Chromium the only browser to install.)

`e2e/a11y.spec.ts`:
```ts
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { openScenario, seekTo } from "./helpers";

test("control room has no serious or critical axe violations", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await seekTo(page, 14_400);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});

test("mobile page has no serious or critical axe violations", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const page = await context.newPage();
  await page.goto("/");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  await context.close();
});
```

`e2e/station3d.spec.ts` (webgl project):
```ts
import { expect, test } from "@playwright/test";

import { openScenario } from "./helpers";

test("the station model loads with every node", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await openScenario(page, "s1_rod_packing");
  await expect(page.locator("canvas")).toBeVisible();
  await page.waitForResponse((r) => r.url().endsWith("/models/ks07.glb") && r.ok());
  await page.waitForTimeout(2_000);
  expect(errors.filter((e) => e.includes("station model is missing nodes"))).toEqual([]);
});

test("selecting in the equipment list keeps the canvas alive (no context loss)", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await page.getByRole("tab", { name: "Equipment" }).click();
  for (const tag of ["K-202", "VS-250", "FL-601", "TK-401"]) {
    await page.getByRole("button", { name: new RegExp(tag) }).click();
  }
  await expect(page.getByText(/3D view unavailable/)).toHaveCount(0);
});
```

`e2e/visual.spec.ts` (webgl project):
```ts
import { expect, test } from "@playwright/test";

import { openScenario, seekTo } from "./helpers";

test.use({ reducedMotion: "reduce" });

test("review camera, S1 at +04:00, paused", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await page.getByRole("combobox", { name: "3D quality" }).selectOption("high");
  await seekTo(page, 14_400);
  await page.waitForTimeout(3_000);
  await expect(page.locator("main[aria-label='Station view']")).toHaveScreenshot("review-s1-0400.png");
});
```

`e2e/fps.spec.ts` (webgl project):
```ts
import { expect, test } from "@playwright/test";

import { measureFps, openScenario, seekTo } from "./helpers";

test("S1 playing at the review camera holds 58 fps on high", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await page.getByRole("combobox", { name: "3D quality" }).selectOption("high");
  await seekTo(page, 9_000);
  await page.getByRole("button", { name: "Play" }).click();
  await page.waitForTimeout(5_000);
  const { avgFps, p95FrameMs } = await measureFps(page, 10_000);
  console.log(`fps avg ${avgFps.toFixed(1)}, p95 frame ${p95FrameMs.toFixed(1)} ms`);
  expect(avgFps).toBeGreaterThanOrEqual(58);
});
```

## Local check stages — add to `STAGES` in `scripts/ci_local.py` (no GitHub Actions)
Append these two entries after `frontend-build`, then run `cd app && uv run ruff format ../scripts` (the `ruff-format` stage checks the layout):
```python
    Stage(
        "replay-build",
        (
            ("app/frontend", ("npm", "run", "build:replay")),
            ("app/frontend", ("npm", "run", "check:replay-bundle")),
        ),
        modes=FULL,
    ),
    Stage("e2e", (("app/frontend", ("npm", "run", "e2e")),), modes=FULL),
```
Extend `test_ci_local.py::test_quick_mode_excludes_full_only_stages` with `assert {"replay-build", "e2e"} <= full and not ({"replay-build", "e2e"} & quick)`. The `webgl` project (`e2e:local`, `e2e:fps`) stays a manual run on the owner's machine.

## Phase evidence — `docs/evidence/2026-11-phase-4-ui.md` (sections, all filled with real output)
1. Screenshots (1440×900 and 1920×1080, S1 at +04:00; S4 during the blowdown; S5 at +04:00 showing no plume) — files in `docs/evidence/`.
2. fps: `npm run e2e:fps` output line, hardware (CPU, GPU string from the perf overlay, RAM), browser + version, display resolution.
3. 3D numbers at the review camera: draw calls, triangles, texture memory (`gl.info`), `ks07.glb` size, `check_glb.py` line.
4. Bundle: `vite build --mode replay` chunk list (main and 3D chunk sizes) and `check:replay-bundle` output.
5. Checks: `check_slop.py` output, impeccable critique summary (issues found / fixed), axe results, `npm run e2e` output.
6. Tests and gates: backend `pytest` summary, frontend `vitest` summary, ruff, typecheck, structure / secrets / env outputs, the **full** security gate (`security-checks` skill, phase-end).

## Steps
- [x] Ask permission for the browser download; install deps (exact); write the config, helpers, specs.
- [x] `npm run e2e` (no-webgl) green; `npm run e2e:local` green on the owner's machine; `npm run e2e:update-baseline` once, look at the baseline image and confirm it is correct before committing it; `npm run e2e:fps` → record.
- [x] Add the two stages; `python scripts/ci_local.py --full --only replay-build,e2e` → both pass; the runner test is green.
- [ ] Full security gate (phase end) per `security-checks`; fix every high/critical.
- [ ] `verify-and-review` against design §9 and the Phase 4 review focus list (README); record findings and fixes.
- [x] Write the evidence file. **Docs:** FRONTEND.md → "Testing" (projects, scripts, baseline policy, fps policy); LOCAL_DEVELOPMENT → "Browser tests". Work-log.
- [ ] **Commit** `test(frontend): add Playwright flows, visual baseline, axe scan and fps check`.
- [ ] `STATUS.md`: "Phase 4 complete — waiting for Gate 4 (UI review)". **STOP.**
