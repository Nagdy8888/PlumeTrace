import { useEffect, useState } from "react";

import { getDataSource, useScenarioStore } from "@/shared/data";
import type { DataSource, DataSourceMode } from "@/shared/data";

/** Scenario opened when the URL does not name a usable one. */
const DEFAULT_SCENARIO_ID = "s1_rod_packing";

/**
 * Pick the first scenario to show: `?scenario=<id>` when it is in the list, else S1 when present,
 * else the first entry.
 *
 * @param ids - Ids of the scenario list, in list order.
 * @param requested - Value of the `scenario` query parameter, or null.
 * @returns The id to select, or null when the list is empty.
 */
function initialScenarioId(ids: string[], requested: string | null): string | null {
  if (requested !== null && ids.includes(requested)) return requested;
  return ids.includes(DEFAULT_SCENARIO_ID) ? DEFAULT_SCENARIO_ID : (ids[0] ?? null);
}

async function bootstrap(source: DataSource): Promise<void> {
  const store = useScenarioStore.getState();
  await store.loadIndex(source);
  const { index, indexStatus } = useScenarioStore.getState();
  if (indexStatus !== "ready") return;
  const requested = new URLSearchParams(window.location.search).get("scenario");
  const id = initialScenarioId(
    index.map((e) => e.id),
    requested,
  );
  if (id !== null) await useScenarioStore.getState().selectScenario(source, id);
}

/**
 * Load the scenario list and open the first scenario once, when the shell mounts.
 *
 * @returns The data-source mode (`live` or `replay`), or null until the source is resolved.
 */
export function useScenarioBootstrap(): DataSourceMode | null {
  const [mode, setMode] = useState<DataSourceMode | null>(null);
  useEffect(() => {
    let active = true;
    void getDataSource().then((source) => {
      if (!active) return undefined; // StrictMode runs the effect twice; only the live run loads
      setMode(source.mode);
      return bootstrap(source);
    });
    return () => {
      active = false;
    };
  }, []);
  return mode;
}

/**
 * Switch to another scenario and record it in the address bar as `?scenario=<id>`.
 *
 * @param id - Scenario id from the list.
 * @returns Resolves when the load has finished (the store holds the result or the error).
 */
export async function chooseScenario(id: string): Promise<void> {
  const url = new URL(window.location.href);
  url.searchParams.set("scenario", id);
  window.history.replaceState(null, "", url);
  await useScenarioStore.getState().selectScenario(await getDataSource(), id);
}

/**
 * Run the failed step again: reload the active scenario, or the list when it never loaded.
 *
 * @returns Resolves when the load has finished.
 */
export async function retryScenarioLoad(): Promise<void> {
  const source = await getDataSource();
  const { activeId, indexStatus, selectScenario } = useScenarioStore.getState();
  if (indexStatus === "ready" && activeId !== null) await selectScenario(source, activeId);
  else await bootstrap(source);
}
