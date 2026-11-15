import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

/** Where scenario data comes from: the local backend or static replay files. */
export type DataSourceMode = "live" | "replay";

/**
 * The one interface every feature uses to get scenario data. Phase 5 adds agent runs.
 *
 * A loaded `ReplayScenario` also carries `keyframes[].sources` (anchor and `rate_kg_h`). That is
 * the simulation input used only to draw the plume: it is not a measurement and not an estimate.
 * No consumer may render it as text or pass it to a format helper.
 */
export interface DataSource {
  readonly mode: DataSourceMode;
  /** List the available scenarios, sorted by id. */
  listScenarios(signal?: AbortSignal): Promise<ReplayIndexEntry[]>;
  /** Load one scenario's full time series. */
  loadScenario(id: string, signal?: AbortSignal): Promise<ReplayScenario>;
}
