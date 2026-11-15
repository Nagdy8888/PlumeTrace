import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { DataSourceError } from "./errors";
import { fetchJson } from "./fetchJson";
import { isScenarioId, parseReplayIndex, parseReplayScenario } from "./validateReplay";

/** Scenario data from the local FastAPI backend (`/api/...`, proxied by Vite in dev). */
export class LiveSource implements DataSource {
  readonly mode = "live" as const;

  /**
   * Read `GET /api/scenarios`.
   *
   * @param signal - Optional abort signal.
   * @returns The scenarios, sorted by id.
   * @throws {DataSourceError} With kind `unreachable` while the backend is down.
   */
  async listScenarios(signal?: AbortSignal): Promise<ReplayIndexEntry[]> {
    return parseReplayIndex(await fetchJson("/api/scenarios", signal));
  }

  /**
   * Read `GET /api/scenarios/<id>/replay`.
   *
   * @param id - A scenario id such as `s1_rod_packing`; anything else is `not_found` without a request.
   * @param signal - Optional abort signal.
   * @returns The validated scenario.
   * @throws {DataSourceError} When the backend is down, the id is unknown or the body is malformed.
   */
  async loadScenario(id: string, signal?: AbortSignal): Promise<ReplayScenario> {
    if (!isScenarioId(id)) throw new DataSourceError("not_found", `Unknown scenario id`);
    const body = await fetchJson(`/api/scenarios/${encodeURIComponent(id)}/replay`, signal);
    return parseReplayScenario(body, id);
  }
}
