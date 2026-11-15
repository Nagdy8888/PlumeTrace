import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useClockStore } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import { makeReplay } from "@/shared/testing/replayFixture";

import { AlarmList } from "./AlarmList";
import { AlarmRow } from "./AlarmRow";

const event = {
  sensor_id: "AT-104",
  window_index: 1,
  window_start_s: 60,
  mean_ppm: 8.4,
  baseline_ppm: 2.1,
  downwind_of_site: true,
};
const scenario = makeReplay({ duration_s: 1200, events: [event] });

describe("AlarmList row click", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useSelectionStore.setState(useSelectionStore.getInitialState());
    useClockStore.getState().reset(1200);
    useClockStore.getState().seek(900);
  });

  it("seeks to the moment the window closed and marks the row current", () => {
    render(<AlarmList scenario={scenario} />);
    const row = screen.getByRole("button", { name: /AT-104/ });
    expect(row).not.toHaveAttribute("aria-current");
    fireEvent.click(row);
    expect(useClockStore.getState().tSeconds).toBe(660);
    expect(useSelectionStore.getState().selectedTag).toBe("AT-104");
    expect(screen.getByRole("button", { name: /AT-104/ })).toHaveAttribute("aria-current", "true");
  });

  it("shows the closing time with its zone label and the 'not downwind' wording", () => {
    render(
      <AlarmList scenario={makeReplay({ events: [{ ...event, downwind_of_site: false }] })} />,
    );
    expect(screen.getByText("06:11:00 UTC")).toBeInTheDocument();
    expect(screen.getByText(/· not downwind of site$/)).toBeInTheDocument();
  });
});

describe("AlarmRow", () => {
  it("keeps aria-current only while selected", () => {
    const { rerender } = render(
      <ul>
        <AlarmRow event={event} simStartUtc="2025-07-15T06:00:00Z" selected onActivate={vi.fn()} />
      </ul>,
    );
    expect(screen.getByRole("button")).toHaveAttribute("aria-current", "true");
    rerender(
      <ul>
        <AlarmRow
          event={event}
          simStartUtc="2025-07-15T06:00:00Z"
          selected={false}
          onActivate={vi.fn()}
        />
      </ul>,
    );
    expect(screen.getByRole("button")).not.toHaveAttribute("aria-current");
  });
});
