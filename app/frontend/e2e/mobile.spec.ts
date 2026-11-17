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
