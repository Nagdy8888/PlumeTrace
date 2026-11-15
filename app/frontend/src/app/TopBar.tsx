import type { JSX } from "react";

import { ScenarioPicker } from "@/features/scenarios";
import { site } from "@/shared/facility/ks07.json";
import { useActiveScenario, useCurrentConditions, type DataSourceMode } from "@/shared/data";
import { formatUtc } from "@/shared/lib/format";
import { useClockStore } from "@/shared/playback";

import { WindReadout } from "./WindReadout";

/** Props of {@link TopBar}. */
export interface TopBarProps {
  /** Where the data comes from, or null until the source is resolved. */
  mode: DataSourceMode | null;
}

const MODE_LABEL: Record<DataSourceMode, string> = {
  live: "Live · local backend",
  replay: "Replay",
};

/** Simulation clock as a UTC time of day, updated once per whole second. */
function UtcClock(): JSX.Element {
  const scenario = useActiveScenario();
  const seconds = useClockStore((s) => Math.floor(s.tSeconds));
  return (
    <span className="font-mono text-xs text-text-1">
      {scenario === null ? "— UTC" : formatUtc(scenario.sim_start_utc, seconds)}
    </span>
  );
}

/**
 * The 48 px top bar: product and station name, scenario picker, data-source mode, wind, the
 * simulation clock in UTC and the always-visible "Simulated" label.
 *
 * @param props - See {@link TopBarProps}.
 * @returns The page header.
 */
export function TopBar({ mode }: TopBarProps): JSX.Element {
  const conditions = useCurrentConditions();
  return (
    <header className="flex h-12 items-center gap-4 border-b border-border-1 bg-surface-1 px-4">
      <h1 className="text-md font-semibold">PlumeTrace</h1>
      <span className="text-text-2">{`Station ${site.id}`}</span>
      <ScenarioPicker />
      {mode === null ? null : <span className="text-sm text-text-2">{MODE_LABEL[mode]}</span>}
      <span className="flex-1" />
      <WindReadout conditions={conditions} />
      <UtcClock />
      <span className="rounded-sm border border-border-2 px-2 py-0.5 text-xs text-text-2">
        Simulated
      </span>
    </header>
  );
}
