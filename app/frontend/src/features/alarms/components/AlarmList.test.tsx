import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import { makeReplay } from "@/shared/testing/replayFixture";

import { AlarmList } from "./AlarmList";

const scenario = makeReplay({
  events: [{ sensor_id: "AT-104", window_index: 1, window_start_s: 60, mean_ppm: 8.4, baseline_ppm: 2.1, downwind_of_site: true }],
});

describe("AlarmList", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useSelectionStore.setState(useSelectionStore.getInitialState());
    useClockStore.getState().reset(1200);
  });
  it("shows the empty state before the event window closes", () => {
    render(<AlarmList scenario={scenario} />);
    expect(screen.getByText("No alarms in this period.")).toBeInTheDocument();
  });
  it("lists a closed event with its numbers and selects the sensor on click", () => {
    useClockStore.getState().seek(660);
    render(<AlarmList scenario={scenario} />);
    expect(screen.getByText("10-min mean 8.4 ppm · baseline 2.1 ppm · downwind of site")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /AT-104/ }));
    expect(useSelectionStore.getState().selectedTag).toBe("AT-104");
  });
});
