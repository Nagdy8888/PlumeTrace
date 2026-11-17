import { expect, test } from "@playwright/test";

import { alarmTimes, openScenario, seekTo, watchProblems } from "./scenarioDriver";

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

// A browser that asks for /favicon.ico gets a 404 console error from the static server. The headless
// shell used by these projects never asks, so the test checks the cause: the page declares an icon
// and that file is served.
test("the page declares a favicon that is served", async ({ page, request }) => {
  await openScenario(page, "s1_rod_packing");
  const icon = page.locator("link[rel='icon']");
  await expect(icon).toHaveAttribute("href", /favicon\.svg$/);
  const response = await request.get((await icon.getAttribute("href")) ?? "");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("image/svg+xml");
});

// Owner ruling (P4 T9 review item 6, extended 2026-11-17): production builds print no React key
// warnings, so the bug class that hit the alarm ticks is only caught by a run that exercises the
// UI. No allow-list: any console error or warning, page error, failed request or HTTP 4xx/5xx fails.
for (const id of ["s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"]) {
  test(`${id}: console, page errors and requests stay clean while the fallback shows`, async ({ page }) => {
    const problems = watchProblems(page);
    await openScenario(page, id);
    await expect(page.getByText(/3D view unavailable on this device/)).toBeVisible();
    await page.getByRole("button", { name: "Play" }).click();
    await page.waitForTimeout(1_000);
    await page.getByRole("button", { name: "Pause" }).click();
    const { times, durationS } = await alarmTimes(page, id);
    for (const t of [...times, durationS]) await seekTo(page, t);
    await page.getByRole("tab", { name: "Equipment" }).click();
    await page.getByRole("button", { name: /VS-250/ }).click();
    expect(problems).toEqual([]);
  });
}
