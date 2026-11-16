import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useQualityTier, useStationStore } from "./store";

describe("quality tier in force", () => {
  beforeEach(() => useStationStore.setState(useStationStore.getInitialState()));

  it("follows the automatic tier while the override is auto", () => {
    const { result } = renderHook(() => useQualityTier());
    expect(result.current).toBe("high");
    act(() => useStationStore.getState().decline());
    expect(result.current).toBe("medium");
  });

  it("a manual override wins over the automatic tier", () => {
    const { result } = renderHook(() => useQualityTier());
    act(() => {
      useStationStore.getState().decline();
      useStationStore.getState().setOverride("high");
    });
    expect(result.current).toBe("high");
    act(() => useStationStore.getState().setOverride("auto"));
    expect(result.current).toBe("medium");
  });
});

describe("automatic decline", () => {
  it("an automatic decline never touches the stored override", () => {
    localStorage.removeItem("plumetrace.quality");
    useStationStore.setState(useStationStore.getInitialState());
    useStationStore.getState().decline();
    expect(useStationStore.getState().override).toBe("auto");
    expect(useStationStore.getState().autoTier).toBe("medium");
    expect(localStorage.getItem("plumetrace.quality")).toBeNull();
  });
});

describe("store start-up", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    localStorage.clear();
  });

  it("starts from a valid stored override and ignores an invalid one", async () => {
    localStorage.setItem("plumetrace.quality", "medium");
    vi.resetModules();
    expect((await import("./store")).useStationStore.getState().override).toBe("medium");
    localStorage.setItem("plumetrace.quality", "ultra");
    vi.resetModules();
    expect((await import("./store")).useStationStore.getState().override).toBe("auto");
  });

  it("ignores a storage error when reading and when writing", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.resetModules();
    const { useStationStore: fresh } = await import("./store");
    expect(fresh.getState().override).toBe("auto");
    fresh.getState().setOverride("low");
    expect(fresh.getState().override).toBe("low");
    vi.restoreAllMocks();
  });

  it("reads prefers-reduced-motion at start and follows changes", async () => {
    let listener: (e: { matches: boolean }) => void = () => undefined;
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      addEventListener: (_: string, fn: typeof listener) => {
        listener = fn;
      },
    }));
    vi.resetModules();
    const { useStationStore: fresh } = await import("./store");
    expect(fresh.getState().reducedMotion).toBe(true);
    listener({ matches: false });
    expect(fresh.getState().reducedMotion).toBe(false);
  });
});
