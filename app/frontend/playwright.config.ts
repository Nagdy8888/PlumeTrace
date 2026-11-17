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
