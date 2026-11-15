import type { JSX } from "react";

import { useScenarioStore } from "@/shared/data";

import { chooseScenario } from "../hooks/useScenarioBootstrap";

/**
 * Native select that lists the scenarios of the data source and switches between them.
 *
 * Changing it loads the scenario (the clock resets, old data is dropped by the store) and writes
 * `?scenario=<id>` to the address bar. It is disabled until the list has loaded.
 *
 * @returns The labelled select.
 */
export function ScenarioPicker(): JSX.Element {
  const index = useScenarioStore((s) => s.index);
  const activeId = useScenarioStore((s) => s.activeId);
  return (
    <select
      aria-label="Scenario"
      value={activeId ?? ""}
      disabled={index.length === 0}
      onChange={(e) => void chooseScenario(e.target.value)}
      className="h-8 rounded-sm border border-border-2 bg-surface-2 px-2 text-sm text-text-1 disabled:text-text-3"
    >
      {activeId === null ? (
        <option value="">{index.length === 0 ? "No scenarios loaded" : "Choose a scenario"}</option>
      ) : null}
      {index.map((entry) => (
        <option key={entry.id} value={entry.id}>
          {entry.title}
        </option>
      ))}
    </select>
  );
}
