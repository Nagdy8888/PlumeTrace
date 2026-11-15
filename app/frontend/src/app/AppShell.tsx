import { useMemo, type JSX } from "react";

import { AlarmList, EVENT_WINDOW_S, StationLog } from "@/features/alarms";
import {
  PlaybackBar,
  ScenarioStatus,
  retryScenarioLoad,
  usePlaybackKeys,
  useScenarioBootstrap,
} from "@/features/scenarios";
import { StationView } from "@/features/station3d";
import { TrendsPanel } from "@/features/trends";
import { useActiveScenario, useScenarioStore, type DataSourceMode } from "@/shared/data";
import { usePlaybackLoop } from "@/shared/playback";

import { TopBar } from "./TopBar";

/** Status of the station view: the index failing counts as a failed scenario load. */
function StationStatus({ mode }: { mode: DataSourceMode | null }): JSX.Element {
  const indexStatus = useScenarioStore((s) => s.indexStatus);
  const status = useScenarioStore((s) => s.status);
  const error = useScenarioStore((s) => s.error);
  return (
    <ScenarioStatus
      mode={mode ?? "live"}
      status={indexStatus === "error" ? "error" : status}
      error={error}
      onRetry={() => void retryScenarioLoad()}
    />
  );
}

/**
 * Top-level layout of the PlumeTrace control room (desktop, 1280 px and wider).
 *
 * Rows: top bar 48 px, working area, trends 220 px, playback bar 44 px. The working area has
 * alarms (320 px), the station view (the 3D scene arrives in Tasks 8 and 9) and the station log
 * (360 px). Below 1280 px the log moves under the alarms. It mounts the data bootstrap, the
 * playback clock loop and the keyboard shortcuts once. The "Simulated" label is always visible
 * because every station value is simulated (design section 8).
 *
 * @returns The application shell.
 */
export function AppShell(): JSX.Element {
  const mode = useScenarioBootstrap();
  usePlaybackLoop();
  usePlaybackKeys();
  const scenario = useActiveScenario();
  const status = useScenarioStore((s) => s.status);
  const eventTimesS = useMemo(
    () => scenario?.events.map((e) => e.window_start_s + EVENT_WINDOW_S) ?? [],
    [scenario],
  );

  return (
    <div className="grid h-full grid-rows-[48px_minmax(0,1fr)_220px_44px] bg-surface-0 text-text-1">
      <TopBar mode={mode} />
      <div className="grid min-h-0 grid-cols-[320px_minmax(0,1fr)] grid-rows-2 min-[1280px]:grid-cols-[320px_minmax(0,1fr)_360px] min-[1280px]:grid-rows-1">
        <div className="col-start-1 row-start-1 grid min-h-0 grid-rows-[minmax(0,1fr)]">
          <AlarmList scenario={scenario} />
        </div>
        <main
          aria-label="Station view"
          className="relative col-start-2 row-span-2 row-start-1 flex min-h-0 items-center justify-center p-6 min-[1280px]:row-span-1"
        >
          <div className="absolute inset-0">
            <StationView />
          </div>
          <StationStatus mode={mode} />
        </main>
        <div className="col-start-1 row-start-2 grid min-h-0 grid-rows-[minmax(0,1fr)] min-[1280px]:col-start-3 min-[1280px]:row-start-1">
          <StationLog scenario={scenario} />
        </div>
      </div>
      <TrendsPanel scenario={scenario} />
      <PlaybackBar
        ready={status === "ready" && scenario !== null}
        simStartUtc={scenario?.sim_start_utc ?? ""}
        eventTimesS={eventTimesS}
      />
    </div>
  );
}
