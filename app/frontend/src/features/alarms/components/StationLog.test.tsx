import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";

import { StationLog } from "./StationLog";

const entry = (t_s: number, kind: string, text: string, tag: string | null = null) => ({
  t_s,
  kind,
  tag,
  text,
});

const scenario = makeReplay({
  duration_s: 6000,
  log: [
    entry(4000, "gauging", "Tank gauged.", "TK-402"),
    entry(5000, "maintenance", "Technician check."),
    entry(600, "shift_note", "Shift handover."),
  ],
});

describe("StationLog", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(6000);
  });

  it("shows the empty state before the first entry", () => {
    render(<StationLog scenario={scenario} />);
    expect(screen.getByText("No log entries yet.")).toBeInTheDocument();
  });

  it("shows an entry exactly at its own time, not a minute-rounded one", () => {
    render(<StationLog scenario={scenario} />);
    act(() => useClockStore.getState().seek(3999));
    expect(screen.queryByText("Tank gauged.")).not.toBeInTheDocument();
    act(() => useClockStore.getState().seek(4000));
    expect(screen.getByText("Tank gauged.")).toBeInTheDocument();
    expect(screen.getByText("Shift handover.")).toBeInTheDocument();
    expect(screen.queryByText("Technician check.")).not.toBeInTheDocument();
  });

  it("lists newest first with a zone-labelled time, a kind label and the tag", () => {
    useClockStore.getState().seek(6000);
    render(<StationLog scenario={scenario} />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      expect.stringContaining("Technician check."),
      expect.stringContaining("Tank gauged."),
      expect.stringContaining("Shift handover."),
    ]);
    expect(items[0]).toHaveTextContent("07:23:20 UTC");
    expect(items[0]).toHaveTextContent("Maintenance");
    expect(items[1]).toHaveTextContent("TK-402");
    expect(items[2]).toHaveTextContent("Shift note");
  });

  it("shows the empty state without a scenario", () => {
    render(<StationLog scenario={null} />);
    expect(screen.getByText("No log entries yet.")).toBeInTheDocument();
  });
});
