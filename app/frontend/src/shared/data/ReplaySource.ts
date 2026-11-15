import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { DataSourceError } from "./errors";
import { fetchJson } from "./fetchJson";
import { isScenarioId, parseReplayIndex, parseReplayScenario } from "./validateReplay";

/** Scenario data from the static files under `/replay/` (the public build and `--mode replay`). */
export class ReplaySource implements DataSource {
  readonly mode = "replay" as const;

  /**
   * Read `/replay/scenarios/index.json`.
   *
   * @param signal - Optional abort signal.
   * @returns The scenarios, sorted by id.
   * @throws {DataSourceError} When the file is missing, unreachable or malformed.
   */
  async listScenarios(signal?: AbortSignal): Promise<ReplayIndexEntry[]> {
    return parseReplayIndex(await fetchJson("/replay/scenarios/index.json", signal));
  }

  /**
   * Read `/replay/scenarios/<id>.json`.
   *
   * @param id - A scenario id such as `s1_rod_packing`; anything else is `not_found` without a request.
   * @param signal - Optional abort signal.
   * @returns The validated scenario.
   * @throws {DataSourceError} When the id is unknown, the file is missing or malformed.
   */
  async loadScenario(id: string, signal?: AbortSignal): Promise<ReplayScenario> {
    if (!isScenarioId(id)) throw new DataSourceError("not_found", `Unknown scenario id`);
    return parseReplayScenario(await fetchJson(`/replay/scenarios/${id}.json`, signal), id);
  }
}
