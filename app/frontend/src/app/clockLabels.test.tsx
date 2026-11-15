import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AlarmList, StationLog } from "@/features/alarms";
import { PlaybackBar } from "@/features/scenarios";
import { useScenarioStore } from "@/shared/data";
import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";

import { TopBar } from "./TopBar";

vi.mock("uplot", () => ({ default: class {} }));

const scenario = makeReplay({
  duration_s: 21600,
  events: [
    {
      sensor_id: "AT-101",
      window_index: 13,
      window_start_s: 7800,
      mean_ppm: 2.1,
      baseline_ppm: 2,
      downwind_of_site: true,
    },
  ],
  log: [{ t_s: 600, kind: "shift_note", tag: null, text: "Handover." }],
});

/** Every `HH:MM` or `HH:MM:SS` in the text, with what follows and precedes it. */
function clockMentions(text: string): { clock: string; before: string; after: string }[] {
  return [...text.matchAll(/\d{2}:\d{2}(?::\d{2})?/g)].map((m) => ({
    clock: m[0],
    before: text.slice(Math.max(0, m.index - 9), m.index),
    after: text.slice(m.index + m[0].length, m.index + m[0].length + 4),
  }));
}

describe("every clock carries a zone label (Gate 3 ruling)", () => {
  beforeEach(() => {
    useScenarioStore.setState({ scenario, status: "ready", activeId: scenario.scenario_id });
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(scenario.duration_s);
    useClockStore.getState().seek(8400);
  });

  it("each HH:MM is a UTC time (followed by ' UTC') or elapsed time (after 'Elapsed +')", () => {
    const { container } = render(
      <>
        <TopBar mode="replay" />
        <AlarmList scenario={scenario} />
        <StationLog scenario={scenario} />
        <PlaybackBar ready simStartUtc={scenario.sim_start_utc} eventTimesS={[]} />
      </>,
    );
    const mentions = clockMentions(container.textContent);
    expect(mentions.length).toBeGreaterThanOrEqual(5);
    for (const m of mentions) {
      const utc = m.after.startsWith(" UTC");
      const elapsed = m.before.endsWith("Elapsed +");
      expect(utc || elapsed, `bare time ${m.clock}`).toBe(true);
    }
  });
});
