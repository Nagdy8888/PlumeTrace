import { useMemo, type JSX } from "react";

import { SAMPLE_STEP_S, useClockStore } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import { Panel } from "@/shared/ui/Panel";
import type { ReplayEvent, ReplayScenario } from "@/shared/types/generated/contract";

import { EVENT_WINDOW_S, visibleEvents } from "../visibleEvents";
import { AlarmRow } from "./AlarmRow";

/** Props of {@link AlarmList}. */
export interface AlarmListProps {
  /** The active scenario, or null while nothing is loaded. */
  scenario: ReplayScenario | null;
}

/**
 * The Alarms panel: detection events whose window has closed, newest first.
 *
 * Reads the clock at whole-minute resolution, so it re-renders once per simulated minute. A row
 * click selects the sensor and moves the clock to the moment the window closed.
 *
 * @param props - See {@link AlarmListProps}.
 * @returns The Alarms panel.
 */
export function AlarmList({ scenario }: AlarmListProps): JSX.Element {
  const minuteS = useClockStore((s) => Math.floor(s.tSeconds / SAMPLE_STEP_S) * SAMPLE_STEP_S);
  const selectedTag = useSelectionStore((s) => s.selectedTag);
  const events = useMemo(() => visibleEvents(scenario, minuteS), [scenario, minuteS]);

  const activate = (event: ReplayEvent): void => {
    useSelectionStore.getState().select(event.sensor_id);
    useClockStore.getState().seek(event.window_start_s + EVENT_WINDOW_S);
  };

  return (
    <Panel title="Alarms" className="rounded-none border-0 border-r">
      <ul aria-live="polite" aria-label="Alarm list">
        {scenario === null || events.length === 0 ? (
          <li className="px-3 py-2 text-sm text-text-2">No alarms in this period.</li>
        ) : (
          events.map((event) => (
            <AlarmRow
              key={`${event.sensor_id}-${event.window_index}`}
              event={event}
              simStartUtc={scenario.sim_start_utc}
              selected={selectedTag === event.sensor_id}
              onActivate={activate}
            />
          ))
        )}
      </ul>
    </Panel>
  );
}
