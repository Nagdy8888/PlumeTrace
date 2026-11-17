import { expect, test } from "@playwright/test";

import { openScenario, seekTo } from "./scenarioDriver";

test.use({ reducedMotion: "reduce" });

test("review camera, S1 at +04:00, paused", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await page.getByRole("combobox", { name: "3D quality" }).selectOption("high");
  await seekTo(page, 14_400);
  await page.waitForTimeout(3_000);
  await expect(page.locator("main[aria-label='Station view']")).toHaveScreenshot("review-s1-0400.png");
});
