import type { JSX } from "react";

import { cn } from "@/shared/lib/cn";
import { formatPpm, formatUtc } from "@/shared/lib/format";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import type { ReplayEvent } from "@/shared/types/generated/contract";

import { EVENT_WINDOW_S } from "../visibleEvents";

/** Props of {@link AlarmRow}. */
export interface AlarmRowProps {
  /** The detection event to show. */
  event: ReplayEvent;
  /** Scenario start (ISO-8601 UTC), the base of the zone-labelled time. */
  simStartUtc: string;
  /** Whether this event's sensor is the selected equipment. */
  selected: boolean;
  /** Called when the row is activated. */
  onActivate: (event: ReplayEvent) => void;
}

/**
 * One alarm: priority badge and word, sensor tag, the UTC time the window closed, and the numbers
 * behind it. All detection events are "Methane rise" at medium priority until triage (Phase 5)
 * assigns real priorities.
 *
 * @param props - See {@link AlarmRowProps}.
 * @returns A list item whose whole row is one button.
 */
export function AlarmRow({ event, simStartUtc, selected, onActivate }: AlarmRowProps): JSX.Element {
  const downwind = event.downwind_of_site ? "downwind of site" : "not downwind of site";
  const closedAtS = event.window_start_s + EVENT_WINDOW_S;
  return (
    <li className="border-b border-border-1 last:border-b-0">
      <button
        type="button"
        aria-current={selected ? "true" : undefined}
        onClick={() => onActivate(event)}
        className={cn(
          "flex w-full flex-col gap-0.5 px-3 py-2 text-left text-sm hover:bg-surface-3",
          selected && "bg-surface-3",
        )}
      >
        <span className="flex items-center gap-2">
          <StatusBadge tone="med">Methane rise</StatusBadge>
          <span className="font-mono text-text-1">{event.sensor_id}</span>
          <span className="ml-auto font-mono text-xs text-text-2">
            {formatUtc(simStartUtc, closedAtS)}
          </span>
        </span>
        <span className="text-text-2">
          {`10-min mean ${formatPpm(event.mean_ppm)} · baseline ${formatPpm(event.baseline_ppm)} · ${downwind}`}
        </span>
      </button>
    </li>
  );
}
