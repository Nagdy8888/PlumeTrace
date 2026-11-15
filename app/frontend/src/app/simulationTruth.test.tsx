import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AlarmList, StationLog } from "@/features/alarms";
import { PlaybackBar } from "@/features/scenarios";
import { TrendsPanel } from "@/features/trends";
import { useScenarioStore } from "@/shared/data";
import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { TopBar } from "./TopBar";

vi.mock("uplot", () => ({
  default: class {
    destroy(): void {}
    setData(): void {}
    redraw(): void {}
    setSize(): void {}
  },
}));

/** Real S1 replay file, as exported to `app/replay/` (the repo copy, not the git-ignored public one). */
const s1 = JSON.parse(
  readFileSync(join(process.cwd(), "..", "replay", "scenarios", "s1_rod_packing.json"), "utf8"),
) as ReplayScenario;

/** Render every view that shows scenario data, at the end of the timeline, and return the DOM. */
function renderAllViews(scenario: ReplayScenario): HTMLElement {
  useScenarioStore.setState({ scenario, status: "ready", activeId: scenario.scenario_id });
  useClockStore.getState().reset(scenario.duration_s);
  useClockStore.getState().seek(scenario.duration_s);
  const { container } = render(
    <>
      <TopBar mode="replay" />
      <AlarmList scenario={scenario} />
      <StationLog scenario={scenario} />
      <TrendsPanel scenario={scenario} />
      <PlaybackBar ready simStartUtc={scenario.sim_start_utc} eventTimesS={[]} />
    </>,
  );
  return container;
}

describe("simulation truth is never rendered (Gate 3 ruling h)", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
  });

  it("S1 fixture: no text, attribute or label holds a source rate or anchor", () => {
    const sources = s1.keyframes.flatMap((k) => k.sources);
    expect(sources.length).toBeGreaterThan(0);
    const html = renderAllViews(s1).innerHTML;
    for (const { anchor_id, rate_kg_h } of sources) {
      expect(html).not.toContain(anchor_id);
      expect(html).not.toMatch(new RegExp(`${rate_kg_h}(\\.0+)?\\s*kg/h`));
    }
    expect(html).not.toContain("kg/h");
  });

  it("a distinctive source rate appears nowhere in the DOM text", () => {
    const scenario = makeReplay({
      keyframes: [
        {
          t_s: 0,
          grid_b64: "",
          stability: "D",
          wind_from_deg: 250,
          wind_speed_m_s: 3.5,
          sources: [{ anchor_id: "VS-250.tip", rate_kg_h: 37.25 }],
        },
      ],
    });
    const container = renderAllViews(scenario);
    for (const needle of ["37.25", "37.3", "37.2", "VS-250"]) {
      expect(container.textContent).not.toContain(needle);
      expect(container.innerHTML).not.toContain(needle);
    }
  });
});
