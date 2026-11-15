import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_STEP_S, useClockStore, usePlaybackLoop, useSampleIndex } from ".";

describe("clock rules", () => {
  beforeEach(() => useClockStore.setState(useClockStore.getInitialState()));

  it("reset keeps the speed and pauses at 0", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.setSpeed(120);
    c.play();
    useClockStore.getState().tick(0.5);
    useClockStore.getState().reset(300);
    expect(useClockStore.getState()).toMatchObject({ tSeconds: 0, durationS: 300, playing: false, speed: 120 });
  });

  it("play at the end restarts from 0", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.seek(600);
    useClockStore.getState().play();
    expect(useClockStore.getState()).toMatchObject({ tSeconds: 0, playing: true });
  });

  it("ignores a zero, negative, NaN or over-1-second step and a non-finite seek", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.play();
    for (const dt of [0, -1, Number.NaN, 1.01]) useClockStore.getState().tick(dt);
    useClockStore.getState().seek(Number.NaN);
    expect(useClockStore.getState().tSeconds).toBe(0);
    useClockStore.getState().tick(1);
    expect(useClockStore.getState().tSeconds).toBe(60);
  });

  it("does not advance while paused", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.play();
    useClockStore.getState().pause();
    useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(0);
  });
});

describe("useSampleIndex", () => {
  beforeEach(() => useClockStore.setState(useClockStore.getInitialState()));

  it("re-renders once per sample, not per tick, and clamps to the last sample", () => {
    useClockStore.getState().reset(600);
    let renders = 0;
    const { result } = renderHook(() => {
      renders += 1;
      return useSampleIndex();
    });
    expect(result.current).toBe(0);
    const before = renders;
    act(() => useClockStore.getState().seek(SAMPLE_STEP_S - 1));
    act(() => useClockStore.getState().seek(SAMPLE_STEP_S - 2));
    expect(renders).toBe(before);
    act(() => useClockStore.getState().seek(SAMPLE_STEP_S));
    expect(result.current).toBe(1);
    act(() => useClockStore.getState().seek(600));
    expect(result.current).toBe(9);
  });

  it("is 0 on an empty timeline", () => {
    const { result } = renderHook(() => useSampleIndex());
    expect(result.current).toBe(0);
  });
});

describe("usePlaybackLoop", () => {
  it("ticks the clock from rAF timestamps and cancels on unmount", () => {
    const callbacks: FrameRequestCallback[] = [];
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => callbacks.push(cb));
    const cancel = vi.fn();
    vi.stubGlobal("cancelAnimationFrame", cancel);
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(600);
    useClockStore.getState().play();
    const { unmount } = renderHook(() => usePlaybackLoop());
    callbacks[0]?.(1000);
    callbacks[1]?.(1500);
    expect(useClockStore.getState().tSeconds).toBe(30);
    unmount();
    expect(cancel).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
