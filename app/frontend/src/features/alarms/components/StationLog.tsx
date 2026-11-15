import { useMemo, type JSX } from "react";

import { formatUtc } from "@/shared/lib/format";
import { useClockStore } from "@/shared/playback";
import { Panel } from "@/shared/ui/Panel";
import type { ReplayScenario } from "@/shared/types/generated/contract";

const KIND_LABEL: Record<string, string> = {
  permit: "Permit",
  gauging: "Gauging",
  maintenance: "Maintenance",
  shift_note: "Shift note",
  calibration: "Calibration",
};

/** Props of {@link StationLog}. */
export interface StationLogProps {
  /** The active scenario, or null while nothing is loaded. */
  scenario: ReplayScenario | null;
}

/**
 * The Station log panel: the operator log entries written up to the current clock time, newest
 * first. Every time carries its zone label (UTC).
 *
 * @param props - See {@link StationLogProps}.
 * @returns The Station log panel.
 */
export function StationLog({ scenario }: StationLogProps): JSX.Element {
  // A primitive selector: the number of entries written so far, so the panel re-renders only when
  // an entry appears. Entries are compared with the exact clock time, not a rounded one.
  const count = useClockStore((s) =>
    scenario === null ? 0 : scenario.log.filter((e) => e.t_s <= s.tSeconds).length,
  );
  const entries = useMemo(
    () =>
      scenario === null
        ? []
        : [...scenario.log]
            .sort((a, b) => a.t_s - b.t_s)
            .slice(0, count)
            .reverse(),
    [scenario, count],
  );

  return (
    <Panel title="Station log" className="rounded-none border-0 border-l">
      <ul aria-label="Station log entries">
        {scenario === null || entries.length === 0 ? (
          <li className="px-3 py-2 text-sm text-text-2">No log entries yet.</li>
        ) : (
          entries.map((entry) => (
            <li
              key={`${entry.t_s}-${entry.kind}-${entry.tag ?? ""}`}
              className="flex flex-col gap-0.5 border-b border-border-1 px-3 py-2 text-sm last:border-b-0"
            >
              <span className="flex items-baseline gap-2">
                <span className="font-mono text-xs text-text-2">
                  {formatUtc(scenario.sim_start_utc, entry.t_s)}
                </span>
                <span className="text-text-1">{KIND_LABEL[entry.kind] ?? entry.kind}</span>
                {entry.tag ? <span className="font-mono text-xs text-text-2">{entry.tag}</span> : null}
              </span>
              <span className="text-text-1">{entry.text}</span>
            </li>
          ))
        )}
      </ul>
    </Panel>
  );
}
