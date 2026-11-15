import type uPlot from "uplot";

import { formatClock } from "@/shared/lib/format";

import type { ChartTheme } from "./chartTheme";
import { cursorPlugin } from "./cursorPlugin";

/** uPlot options without the size, which the wrapper takes from its container. */
export type ChartOptions = Omit<uPlot.Options, "width" | "height">;

const FONT = '11px "IBM Plex Mono", ui-monospace, monospace';
/** Tick spacings in seconds: 5 min up to 4 h, so labels fall on whole minutes. */
const X_TICK_STEPS_S = [300, 600, 1800, 3600, 7200, 14400];
/** Wind direction axis: the four cardinal degrees plus north again. */
const DIRECTION_TICKS_DEG = [0, 90, 180, 270, 360];

function axis(theme: ChartTheme, extra: uPlot.Axis = {}): uPlot.Axis {
  return {
    stroke: theme.text2,
    font: FONT,
    grid: { stroke: theme.grid, width: 1 },
    ticks: { stroke: theme.grid, width: 1 },
    ...extra,
  };
}

/** Elapsed-time x axis: values are seconds since the start, labelled `+HH:MM`. */
function elapsedAxis(theme: ChartTheme): uPlot.Axis {
  return axis(theme, {
    incrs: X_TICK_STEPS_S,
    space: 72,
    values: (_u, splits) => splits.map((v) => formatClock(v)),
  });
}

/** Linear y range from 0 to the largest value (with headroom); 1 when there is no data yet. */
const zeroBased: uPlot.Scale.Range = (_u, _min, max) => [0, max > 0 ? max * 1.1 : 1];

const baseOptions = (theme: ChartTheme, getTimeS: () => number, stepS: number) => ({
  legend: { show: false },
  cursor: { show: false },
  plugins: [cursorPlugin(theme.focus, getTimeS, stepS)],
});

/**
 * Options of the methane chart: one line per sensor, highlighted sensors in the accent colour.
 *
 * @param theme - Resolved token colours.
 * @param ids - Sensor ids in series order (draw highlighted ones last so they sit on top).
 * @param highlighted - Sensor ids drawn 1.5 px in the accent colour; the rest are 1 px, quiet.
 * @param getTimeS - Current simulation time in seconds (for the cursor line).
 * @param stepS - Sample length in seconds.
 * @returns The chart options (without size).
 */
export function methaneOptions(
  theme: ChartTheme,
  ids: string[],
  highlighted: string[],
  getTimeS: () => number,
  stepS: number,
): ChartOptions {
  return {
    ...baseOptions(theme, getTimeS, stepS),
    scales: { x: { time: false }, y: { range: zeroBased } },
    axes: [elapsedAxis(theme), axis(theme, { size: 44 })],
    series: [
      {},
      ...ids.map((id): uPlot.Series => {
        const hot = highlighted.includes(id);
        return {
          label: id,
          stroke: hot ? theme.accent : theme.text3,
          width: hot ? 1.5 : 1,
          points: { show: false },
          spanGaps: false,
        };
      }),
    ],
  };
}

/**
 * Options of the wind chart: speed as a line on the left axis, direction as points on the right.
 *
 * @param theme - Resolved token colours.
 * @param getTimeS - Current simulation time in seconds (for the cursor line).
 * @param stepS - Sample length in seconds.
 * @returns The chart options (without size).
 */
export function windOptions(theme: ChartTheme, getTimeS: () => number, stepS: number): ChartOptions {
  return {
    ...baseOptions(theme, getTimeS, stepS),
    scales: { x: { time: false }, speed: { range: zeroBased }, dir: { range: [0, 360] } },
    axes: [
      elapsedAxis(theme),
      axis(theme, { scale: "speed", size: 44 }),
      axis(theme, {
        scale: "dir",
        side: 1,
        size: 44,
        grid: { show: false },
        splits: DIRECTION_TICKS_DEG,
      }),
    ],
    series: [
      {},
      { label: "Wind speed", scale: "speed", stroke: theme.text2, width: 1, points: { show: false } },
      {
        label: "Wind from",
        scale: "dir",
        stroke: theme.text3,
        paths: () => null,
        points: { show: true, size: 3, width: 0, fill: theme.text3 },
      },
    ],
  };
}
