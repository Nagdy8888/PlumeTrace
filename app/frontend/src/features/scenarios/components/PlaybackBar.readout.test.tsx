import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";

import { PlaybackBar } from "./PlaybackBar";

describe("PlaybackBar readout and ticks", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(21600);
    useClockStore.getState().seek(7260);
  });

  it("labels the elapsed time and the UTC time of day", () => {
    const { container } = render(
      <PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />,
    );
    expect(container.textContent).toContain("Elapsed +02:01 · 08:01:00 UTC");
  });

  it("hides the UTC part until a scenario is loaded", () => {
    const { container } = render(<PlaybackBar ready={false} simStartUtc="" eventTimesS={[]} />);
    expect(container.textContent).toContain("Elapsed");
    expect(container.textContent).not.toContain("UTC");
    expect(container.textContent).not.toContain("·");
  });

  it("draws one aria-hidden tick per alarm at its share of the timeline", () => {
    const { container } = render(
      <PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[5400, 10800]} />,
    );
    const ticks = [...container.querySelectorAll<HTMLElement>("span[style]")];
    expect(ticks.map((t) => t.style.left)).toEqual(["25%", "50%"]);
    expect(ticks[0]?.parentElement).toHaveAttribute("aria-hidden", "true");
  });

  it("gives the slider the whole timeline in one-minute steps", () => {
    render(<PlaybackBar ready simStartUtc="2025-07-15T06:00:00Z" eventTimesS={[]} />);
    const slider = screen.getByRole("slider", { name: "Simulation time" });
    expect(slider).toHaveAttribute("max", "21600");
    expect(slider).toHaveAttribute("step", "60");
    expect(slider).toHaveValue("7260");
  });
});
