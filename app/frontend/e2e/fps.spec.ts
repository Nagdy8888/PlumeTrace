import { expect, test } from "@playwright/test";

import { describeGpu, installGpuProbe, sampleFrames } from "./gpuProbe";
import { measureFps, openScenario, seekTo } from "./scenarioDriver";

test("S1 playing at the review camera holds 58 fps on high", async ({ page, browser }) => {
  await openScenario(page, "s1_rod_packing");
  await page.getByRole("combobox", { name: "3D quality" }).selectOption("high");
  await seekTo(page, 9_000);
  await page.getByRole("button", { name: "Play" }).click();
  await page.waitForTimeout(5_000);
  const { avgFps, p95FrameMs } = await measureFps(page, 10_000);
  console.log(`fps avg ${avgFps.toFixed(1)}, p95 frame ${p95FrameMs.toFixed(1)} ms`);
  console.log(await describeGpu(page, browser.version()));
  expect(avgFps).toBeGreaterThanOrEqual(58);
});

/** Owner definition of the draw-call budget (P4 T9 review): "300 as rendered". */
const DRAW_CALL_BUDGET = 300;

// The budget is the sum of `gl.info.render.calls` over every render call of one displayed frame
// (shadow, scene and post passes), REVIEW_CAMERA, 1920x1080 viewport, clock playing. S1 +02:20 is
// 8400 s; the S4 blowdown peak is the key frame with the highest total source rate, 7200 s.
for (const [id, seconds, label] of [
  ["s1_rod_packing", 8_400, "S1 +02:20"],
  ["s4_planned_blowdown", 7_200, "S4 blowdown peak"],
] as const) {
  for (const tier of ["high", "medium", "low"] as const) {
    test(`draw calls: ${label}, ${tier} tier, playing at 1080p stay within the budget`, async ({ page, browser }) => {
      await installGpuProbe(page);
      await openScenario(page, id);
      await page.getByRole("combobox", { name: "3D quality" }).selectOption(tier);
      await seekTo(page, seconds);
      await page.getByRole("button", { name: "Play" }).click();
      await page.waitForTimeout(3_000);
      const s = await sampleFrames(page, 120);
      const mb = (s.textureBytes / 1024 / 1024).toFixed(1);
      console.log(
        `draw calls ${label} ${tier}: max ${s.maxCalls}, median ${s.medianCalls} (GL draws max ${s.maxGlDraws}), ` +
          `triangles median ${s.medianTriangles}, max ${s.maxTriangles}, textures ${s.textures} (${mb} MiB via texStorage2D, ` +
          `unmapped formats ${s.unmappedFormats.length}), geometries ${s.geometries}, frames ${s.frames}`,
      );
      console.log(await describeGpu(page, browser.version()));
      expect(s.frames).toBeGreaterThan(60);
      expect(s.maxCalls).toBeLessThanOrEqual(DRAW_CALL_BUDGET);
    });
  }
}
