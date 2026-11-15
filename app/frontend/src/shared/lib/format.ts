const POINTS_16 = [
  "N",
  "NNE",
  "NE",
  "ENE",
  "E",
  "ESE",
  "SE",
  "SSE",
  "S",
  "SSW",
  "SW",
  "WSW",
  "W",
  "WNW",
  "NW",
  "NNW",
] as const;

const NO_VALUE = "—";

const pad2 = (n: number): string => String(n).padStart(2, "0");

/**
 * Format a methane concentration.
 *
 * @param value - Concentration in ppm, or null when there is no reading.
 * @returns `"—"` for null or non-finite input, otherwise the value with its unit: one decimal
 *   below 100 (`"4.2 ppm"`), none at or above 100 (`"123 ppm"`).
 */
export function formatPpm(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return NO_VALUE;
  return value < 100 ? `${value.toFixed(1)} ppm` : `${value.toFixed(0)} ppm`;
}

/**
 * Format a single emission-rate value.
 *
 * Display rule (owner decision R1-R4, Gate 3): a leak rate is only ever shown to the
 * operator as an interval, "p05-p95 kg/h (median p50)" with 2 significant figures and the
 * label "model estimate". This helper formats one number with one decimal and cannot
 * enforce that, so a UI component must call it once per interval bound and add the
 * interval and the label itself; never render its result alone as "the" rate.
 *
 * @param kgPerHour - Rate in kg/h, or null when there is no estimate.
 * @returns `"—"` for null or non-finite input, otherwise one decimal plus `" kg/h"`.
 */
export function formatRate(kgPerHour: number | null): string {
  if (kgPerHour === null || !Number.isFinite(kgPerHour)) return NO_VALUE;
  return `${kgPerHour.toFixed(1)} kg/h`;
}

/**
 * Format a simulation instant as a UTC clock time.
 *
 * Display rule (owner decision, Gate 3): every clock shown in the UI carries a zone label.
 * The result always ends in `" UTC"`; a station-local time must be built separately with its
 * own `"UTC+5 station time"` label, never by dropping the suffix. Hours wrap at 24 (the date
 * is not shown).
 *
 * @param simStartUtc - Simulation start as an ISO-8601 UTC string (`"2025-07-15T06:00:00Z"`).
 * @param tSeconds - Seconds elapsed since the simulation start.
 * @returns `"HH:MM:SS UTC"`, or `"—"` when the start is not a valid date or `tSeconds` is not finite.
 */
export function formatUtc(simStartUtc: string, tSeconds: number): string {
  const ms = Date.parse(simStartUtc) + tSeconds * 1000;
  if (!Number.isFinite(ms)) return NO_VALUE;
  const d = new Date(ms);
  return `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())} UTC`;
}

/**
 * Format elapsed simulation time as `"+HH:MM"`.
 *
 * This is a duration since the simulation start, not a time of day, so it carries no zone
 * label; the surrounding UI must label it as elapsed time and show a zone-labelled clock
 * (see {@link formatUtc}) for any time of day. Seconds are truncated.
 *
 * @param tSeconds - Elapsed seconds (a negative value gets a `"-"` sign).
 * @returns `"+HH:MM"`, for example `7260` gives `"+02:01"`; `"—"` for non-finite input.
 */
export function formatClock(tSeconds: number): string {
  if (!Number.isFinite(tSeconds)) return NO_VALUE;
  const totalMinutes = Math.floor(Math.abs(tSeconds) / 60);
  const sign = tSeconds < 0 ? "-" : "+";
  return `${sign}${pad2(Math.floor(totalMinutes / 60))}:${pad2(totalMinutes % 60)}`;
}

/**
 * Convert a wind direction to a 16-point compass name.
 *
 * Sectors are 22.5 degrees wide and centred on the point (north covers 348.75 up to 11.25;
 * the upper edge belongs to the next sector).
 *
 * @param fromDeg - Direction the wind blows from, in degrees clockwise from north (any real number).
 * @returns One of `N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW`.
 */
export function compass16(fromDeg: number): string {
  const deg = ((fromDeg % 360) + 360) % 360;
  return POINTS_16[Math.floor((deg + 11.25) / 22.5) % 16] ?? "N";
}
