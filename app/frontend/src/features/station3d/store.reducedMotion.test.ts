import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("reduced motion", () => {
  it("is on in the store when the OS asks for reduced motion", async () => {
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: q === "(prefers-reduced-motion: reduce)",
      media: q,
      addEventListener: () => undefined,
    }));
    vi.resetModules();
    const { useStationStore } = await import("./store");
    expect(useStationStore.getState().reducedMotion).toBe(true);
  });
});
