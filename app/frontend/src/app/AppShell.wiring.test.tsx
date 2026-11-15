import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetDataSourceForTests, useScenarioStore } from "@/shared/data";
import { useClockStore } from "@/shared/playback";

import { AppShell } from "./AppShell";

describe("AppShell wiring", () => {
  beforeEach(() => {
    resetDataSourceForTests();
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows 'Backend not reachable' with the start command when the backend is down", async () => {
    render(<AppShell />);
    expect(
      await screen.findByRole("heading", { name: "Backend not reachable" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/uv run uvicorn plumetrace\.api\.main:app/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("mounts the playback loop: the clock advances with animation frames while playing", async () => {
    const frames: FrameRequestCallback[] = [];
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => frames.push(cb));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
    render(<AppShell />);
    await screen.findByRole("heading", { name: "Backend not reachable" });
    useClockStore.setState({ durationS: 3600, playing: true, speed: 60 });
    const frame = frames.at(-1) as FrameRequestCallback;
    frame(1000);
    expect(useClockStore.getState().tSeconds).toBe(0);
    // The loop reschedules itself, so the newest callback is the next frame: 0.5 s x 60 = 30 s.
    (frames.at(-1) as FrameRequestCallback)(1500);
    expect(useClockStore.getState().tSeconds).toBe(30);
  });
});
