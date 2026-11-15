import type { ReplayEvent, ReplayScenario } from "@/shared/types/generated/contract";

/** Length of one detection window in seconds; matches the backend `WINDOW_S`. */
export const EVENT_WINDOW_S = 600;

/**
 * The detection events an operator has seen at clock time `tSeconds`.
 *
 * An event is raised when its 10-minute window closes, so it is visible only from
 * `window_start_s + EVENT_WINDOW_S`. Newest window first; equal windows are ordered by sensor id.
 *
 * @param scenario - The active scenario, or null.
 * @param tSeconds - Simulation time in seconds since the scenario start.
 * @returns The visible events (empty without a scenario).
 */
export function visibleEvents(scenario: ReplayScenario | null, tSeconds: number): ReplayEvent[] {
  if (scenario === null) return [];
  return scenario.events
    .filter((e) => e.window_start_s + EVENT_WINDOW_S <= tSeconds)
    .sort((a, b) => b.window_start_s - a.window_start_s || a.sensor_id.localeCompare(b.sensor_id));
}
