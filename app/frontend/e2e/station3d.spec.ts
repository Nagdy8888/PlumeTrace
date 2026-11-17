import { expect, test } from "@playwright/test";

import { alarmTimes, openScenario, seekTo, watchProblems } from "./scenarioDriver";

test("the station model loads with every node", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await openScenario(page, "s1_rod_packing");
  // Owner ruling P4 T11 review (2): scoped to the station view; page.locator("canvas") also matches the two uPlot chart canvases (strict-mode violation).
  await expect(page.locator("main[aria-label='Station view'] canvas")).toBeVisible();
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

// Owner ruling (P4 T9 review item 6): zero console errors with the 3D scene running. Warnings are
// not ignored either, except the exact texts listed here, each known and benign. Both are three.js
// 0.187.0 deprecation notices, seen on every run in this scene; neither changes what is drawn.
const BENIGN_WARNINGS: readonly string[] = [
  // R3F 9.8.2 creates a THREE.Clock for its frame loop; three 0.187.0 deprecates the class.
  "THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.",
  // R3F's `shadows` prop selects PCFSoftShadowMap; three 0.187.0 maps it to PCFShadowMap and says so once.
  "THREE.WebGLShadowMap: PCFSoftShadowMap has been removed. Using PCFShadowMap instead.",
];

test("the 3D scene runs S1 without console errors, page errors or failed requests", async ({ page }) => {
  const problems = watchProblems(page, BENIGN_WARNINGS);
  await openScenario(page, "s1_rod_packing");
  await expect(page.locator("main[aria-label='Station view'] canvas")).toBeVisible();
  await page.getByRole("button", { name: "Play" }).click();
  await page.waitForTimeout(2_000);
  await page.getByRole("button", { name: "Pause" }).click();
  const { times, durationS } = await alarmTimes(page, "s1_rod_packing");
  for (const t of [...times, durationS]) await seekTo(page, t);
  await page.getByRole("tab", { name: "Equipment" }).click();
  for (const tag of ["K-202", "VS-250"]) await page.getByRole("button", { name: new RegExp(tag) }).click();
  await page.waitForTimeout(1_000);
  expect(problems).toEqual([]);
});
