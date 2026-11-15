import { create } from "zustand";

import { useClockStore } from "@/shared/playback";
import type { ReplayIndexEntry, ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { DataSourceError } from "./errors";
import { isAbortError } from "./fetchJson";

/** Load status of the scenario list or of the active scenario. */
export type LoadStatus = "idle" | "loading" | "ready" | "error";

/** State and actions of the scenario store. */
export interface ScenarioState {
  /** Available scenarios, sorted by id. */
  index: ReplayIndexEntry[];
  indexStatus: LoadStatus;
  /** Id of the scenario the user chose, or null. */
  activeId: string | null;
  /** The loaded scenario; null while loading, on error and before any choice. */
  scenario: ReplayScenario | null;
  status: LoadStatus;
  /** The most recent failure (list or scenario); the UI chooses its message from `kind`. */
  error: DataSourceError | null;
  /** Counts selections; a response whose number is no longer current is dropped. */
  requestSeq: number;
  /** Load the scenario list. */
  loadIndex: (source: DataSource) => Promise<void>;
  /** Choose a scenario: reset the clock, load it, and ignore the answer if a newer choice exists. */
  selectScenario: (source: DataSource, id: string) => Promise<void>;
}

let controller: AbortController | null = null;

function toDataSourceError(error: unknown): DataSourceError {
  if (error instanceof DataSourceError) return error;
  return new DataSourceError("invalid", error instanceof Error ? error.message : "Unexpected error");
}

/**
 * Which scenario is active and its load status. A business-neutral container: features read it
 * through `useActiveScenario` and `useScenarioStatus`.
 *
 * The loaded `ReplayScenario` includes `keyframes[].sources` (simulation truth for drawing the
 * plume only). No selector or hook here exposes it as display text.
 */
export const useScenarioStore = create<ScenarioState>()((set, get) => ({
  index: [],
  indexStatus: "idle",
  activeId: null,
  scenario: null,
  status: "idle",
  error: null,
  requestSeq: 0,
  loadIndex: async (source) => {
    set({ indexStatus: "loading", error: null });
    try {
      set({ index: await source.listScenarios(), indexStatus: "ready" });
    } catch (error) {
      if (isAbortError(error)) return;
      set({ indexStatus: "error", error: toDataSourceError(error) });
    }
  },
  selectScenario: async (source, id) => {
    controller?.abort();
    controller = new AbortController();
    const seq = get().requestSeq + 1;
    set({ activeId: id, scenario: null, status: "loading", error: null, requestSeq: seq });
    useClockStore.getState().reset(0);
    try {
      const scenario = await source.loadScenario(id, controller.signal);
      if (get().requestSeq !== seq) return;
      set({ scenario, status: "ready" });
      useClockStore.getState().reset(scenario.duration_s);
    } catch (error) {
      if (isAbortError(error) || get().requestSeq !== seq) return;
      set({ status: "error", error: toDataSourceError(error) });
    }
  },
}));

/** @returns The loaded scenario, or null while loading, on error and before any choice. */
export function useActiveScenario(): ReplayScenario | null {
  return useScenarioStore((s) => s.scenario);
}

/** @returns The load status of the active scenario. */
export function useScenarioStatus(): LoadStatus {
  return useScenarioStore((s) => s.status);
}
