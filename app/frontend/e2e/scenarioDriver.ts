import { expect, type Page } from "@playwright/test";

/** Playwright locator name of the playback slider. */
const SLIDER = "Simulation time";

/**
 * Open the replay build on one scenario and wait until the playback slider is enabled.
 *
 * @param page - The Playwright page.
 * @param id - Scenario id, for example `s1_rod_packing`.
 */
export async function openScenario(page: Page, id: string): Promise<void> {
  await page.goto(`/?scenario=${id}`);
  await expect(page.getByRole("slider", { name: SLIDER })).toBeEnabled();
}

/**
 * Move the simulation clock by filling the `Simulation time` slider, then wait one animation frame.
 *
 * @param page - The Playwright page.
 * @param seconds - Target clock time in seconds since the scenario start.
 */
export async function seekTo(page: Page, seconds: number): Promise<void> {
  await page.getByRole("slider", { name: SLIDER }).fill(String(seconds));
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
}

/** Frame-rate figures of {@link measureFps}. */
export interface FpsResult {
  /** Mean frames per second over the sampling window. */
  avgFps: number;
  /** 95th percentile of the frame-to-frame time in milliseconds. */
  p95FrameMs: number;
}

/**
 * Count `requestAnimationFrame` callbacks for `ms` milliseconds in the page.
 *
 * @param page - The Playwright page.
 * @param ms - Sampling time in milliseconds.
 * @returns Average frame rate and the 95th percentile of the frame times.
 */
export async function measureFps(page: Page, ms: number): Promise<FpsResult> {
  return page.evaluate(
    (durationMs) =>
      new Promise<{ avgFps: number; p95FrameMs: number }>((resolve) => {
        const stamps: number[] = [];
        const tick = (now: number): void => {
          stamps.push(now);
          if (now - (stamps[0] ?? now) < durationMs) {
            requestAnimationFrame(tick);
            return;
          }
          const deltas = stamps.slice(1).map((t, i) => t - (stamps[i] ?? t));
          const sorted = [...deltas].sort((a, b) => a - b);
          const p95 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))] ?? 0;
          const elapsed = (stamps[stamps.length - 1] ?? 0) - (stamps[0] ?? 0);
          resolve({ avgFps: elapsed > 0 ? (deltas.length * 1000) / elapsed : 0, p95FrameMs: p95 });
        };
        requestAnimationFrame(tick);
      }),
    ms,
  );
}

/**
 * Record everything a clean page must not produce: console errors and warnings, uncaught page
 * errors, failed requests and HTTP responses with status 400 or above. Call before navigating.
 *
 * @param page - The Playwright page.
 * @param ignoreWarnings - Exact console warning texts that are known and benign (listed by the caller).
 * @returns The live list of problem descriptions; empty means the page stayed clean.
 */
export function watchProblems(page: Page, ignoreWarnings: readonly string[] = []): string[] {
  const problems: string[] = [];
  page.on("console", (m) => {
    const type = m.type();
    if (type === "error" || (type === "warning" && !ignoreWarnings.includes(m.text()))) {
      problems.push(`console.${type}: ${m.text()}`);
    }
  });
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("requestfailed", (r) => problems.push(`request failed: ${r.url()} ${r.failure()?.errorText ?? ""}`));
  page.on("response", (r) => {
    if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`);
  });
  return problems;
}

/**
 * Read the replay file of a scenario through the running preview server and return the clock times
 * at which its alarms become visible (`window_start_s` plus the 10-minute window) and its duration.
 *
 * @param page - The Playwright page (its request context is used).
 * @param id - Scenario id.
 * @returns Alarm times in seconds, ascending, and the scenario duration in seconds.
 */
export async function alarmTimes(page: Page, id: string): Promise<{ times: number[]; durationS: number }> {
  const response = await page.request.get(`/replay/scenarios/${id}.json`);
  const body = (await response.json()) as { duration_s: number; events: { window_start_s: number }[] };
  const times = [...new Set(body.events.map((e) => e.window_start_s + 600))].sort((a, b) => a - b);
  return { times, durationS: body.duration_s };
}
