import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";

import { PlaybackBar } from "./PlaybackBar";

describe("PlaybackBar", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(21600);
  });
  it("toggles play and pause", () => {
    render(<PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    expect(useClockStore.getState().playing).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("changes speed through the radio group", () => {
    render(<PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    fireEvent.click(screen.getByRole("radio", { name: "120×" }));
    expect(useClockStore.getState().speed).toBe(120);
  });
  it("is disabled while the scenario is not ready", () => {
    render(<PlaybackBar ready={false} simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    expect(screen.getByRole("button", { name: "Play" })).toBeDisabled();
    expect(screen.getByRole("slider", { name: "Simulation time" })).toBeDisabled();
  });
});
