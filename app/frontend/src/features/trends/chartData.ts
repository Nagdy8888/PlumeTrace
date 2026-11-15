import { visibleEvents } from "@/features/alarms";
import type { ReplayScenario } from "@/shared/types/generated/contract";

/** Methane trend data: shared x axis and one series per sensor. */
export interface MethaneData {
  /** Seconds since the scenario start, `x[i] = i * step_s`. */
  x: number[];
  /** One array per sensor (same order as `ids`); `null` after the current sample. */
  series: (number | null)[][];
  /** Sensor ids, in the order of `scenario.sensors`. */
  ids: string[];
}

/** Wind trend data on the same x axis. */
export interface WindData {
  /** Seconds since the scenario start. */
  x: number[];
  /** Wind speed in m/s; `null` after the current sample. */
  speed: (number | null)[];
  /** Direction the wind blows from, degrees; `null` after the current sample. */
  fromDeg: (number | null)[];
}

const xAxis = (scenario: ReplayScenario): number[] =>
  scenario.wind_speed_m_s.map((_, i) => i * scenario.step_s);

/** Keep the history up to and including the current sample; later samples become null. */
function history<T>(values: readonly T[], sampleIndex: number): (T | null)[] {
  return values.map((v, i) => (i > sampleIndex ? null : v));
}

/**
 * Methane readings of every sensor, limited to the history up to the current sample.
 *
 * @param scenario - The active scenario.
 * @param sampleIndex - Index of the current 60 s sample; later entries are `null`.
 * @returns The x axis, one series per sensor and the sensor ids.
 */
export function methaneData(scenario: ReplayScenario, sampleIndex: number): MethaneData {
  const ids = scenario.sensors.map((s) => s.id);
  return {
    x: xAxis(scenario),
    series: ids.map((id) => history(scenario.series[id] ?? [], sampleIndex)),
    ids,
  };
}

/**
 * Reorder the methane series so the highlighted sensors come last, i.e. are drawn on top.
 *
 * @param data - Methane data in scenario order.
 * @param highlighted - Sensor ids to draw last.
 * @returns A new object with the same x axis; the order inside each group is kept.
 */
export function highlightLast(data: MethaneData, highlighted: string[]): MethaneData {
  const order = data.ids
    .map((id, i) => ({ id, i, hot: highlighted.includes(id) }))
    .sort((a, b) => Number(a.hot) - Number(b.hot) || a.i - b.i);
  return {
    x: data.x,
    ids: order.map((o) => o.id),
    series: order.map((o) => data.series[o.i] ?? []),
  };
}

/**
 * Wind speed and direction, limited to the history up to the current sample.
 *
 * @param scenario - The active scenario.
 * @param sampleIndex - Index of the current 60 s sample; later entries are `null`.
 * @returns The x axis, speed in m/s and direction in degrees.
 */
export function windData(scenario: ReplayScenario, sampleIndex: number): WindData {
  return {
    x: xAxis(scenario),
    speed: history(scenario.wind_speed_m_s, sampleIndex),
    fromDeg: history(scenario.wind_from_deg, sampleIndex),
  };
}

/**
 * Sensors drawn in the accent colour: the selected one (if it is a methane sensor) and every
 * sensor with a visible alarm.
 *
 * @param scenario - The active scenario.
 * @param tSeconds - Simulation time in seconds.
 * @param selectedTag - The selected equipment tag, or null.
 * @returns Sorted, unique sensor ids.
 */
export function highlightedSensors(
  scenario: ReplayScenario,
  tSeconds: number,
  selectedTag: string | null,
): string[] {
  const ids = new Set(visibleEvents(scenario, tSeconds).map((e) => e.sensor_id));
  if (selectedTag !== null && scenario.sensors.some((s) => s.id === selectedTag)) {
    ids.add(selectedTag);
  }
  return [...ids].sort();
}
