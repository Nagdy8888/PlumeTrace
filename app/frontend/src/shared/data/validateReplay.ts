import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

import { DataSourceError } from "./errors";

const SCENARIO_ID = /^s[0-9]+_[a-z0-9_]+$/;

/**
 * Say whether a string has the shape of a scenario id (`s1_rod_packing`).
 *
 * Both sources check this before building a URL, so an id can never reach another path.
 *
 * @param id - Candidate id.
 * @returns True when the id may be requested.
 */
export function isScenarioId(id: string): boolean {
  return SCENARIO_ID.test(id);
}

function invalid(what: string): DataSourceError {
  return new DataSourceError("invalid", `Replay data rejected: ${what}`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasLength(value: unknown, n: number): boolean {
  return Array.isArray(value) && value.length === n;
}

/**
 * Check a parsed replay file and return it typed.
 *
 * Checks (the Python model checks the rest when the file is written): an object;
 * `schema_version === 1`; `simulated === true`; `scenario_id === expectedId`; `step_s > 0`;
 * with `n = round(duration_s / step_s)` the wind lists, `stability` and every `series` array have
 * `n` entries; every `series` tag has a `units` entry.
 *
 * @param data - The parsed JSON.
 * @param expectedId - The id that was requested.
 * @returns The same value, typed as a replay scenario.
 * @throws {DataSourceError} With kind `invalid` when a check fails.
 */
export function parseReplayScenario(data: unknown, expectedId: string): ReplayScenario {
  if (!isRecord(data)) throw invalid("not an object");
  if (data.schema_version !== 1) throw invalid("schema_version is not 1");
  if (data.simulated !== true) throw invalid("file is not marked simulated");
  if (data.scenario_id !== expectedId) throw invalid("scenario_id does not match the request");
  const { step_s: step, duration_s: duration, series, units } = data;
  if (typeof step !== "number" || !(step > 0)) throw invalid("step_s must be > 0");
  if (typeof duration !== "number") throw invalid("duration_s is not a number");
  const n = Math.round(duration / step);
  for (const key of ["wind_speed_m_s", "wind_from_deg", "stability"]) {
    if (!hasLength(data[key], n)) throw invalid(`${key} must have ${n} samples`);
  }
  if (!isRecord(series) || !isRecord(units)) throw invalid("series and units must be objects");
  for (const [tag, values] of Object.entries(series)) {
    if (!hasLength(values, n)) throw invalid(`series ${tag} must have ${n} samples`);
    if (typeof units[tag] !== "string") throw invalid(`series ${tag} has no unit`);
  }
  return data as unknown as ReplayScenario;
}

function toEntry(value: unknown): ReplayIndexEntry {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.title !== "string" ||
    typeof value.duration_h !== "number" ||
    typeof value.is_mvp !== "boolean"
  ) {
    throw invalid("malformed scenario entry");
  }
  return { id: value.id, title: value.title, duration_h: value.duration_h, is_mvp: value.is_mvp };
}

/**
 * Check a scenario list and return its entries sorted by id.
 *
 * Accepts the replay `index.json` object (`schema_version === 1` and a `scenarios` array) or a
 * bare array (the live API answers `list[ScenarioSummary]`).
 *
 * @param data - The parsed JSON.
 * @returns The entries, sorted by id.
 * @throws {DataSourceError} With kind `invalid` when the shape or an entry is wrong.
 */
export function parseReplayIndex(data: unknown): ReplayIndexEntry[] {
  let raw: unknown = data;
  if (isRecord(data)) {
    if (data.schema_version !== 1) throw invalid("index schema_version is not 1");
    raw = data.scenarios;
  }
  if (!Array.isArray(raw)) throw invalid("scenario list is not an array");
  return raw.map(toEntry).sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}
