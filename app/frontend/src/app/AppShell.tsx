import { useMemo, type JSX } from "react";

import { EVENT_WINDOW_S, StationLog } from "@/features/alarms";
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

import { LeftColumn } from "./LeftColumn";
import { MobilePage } from "./MobilePage";
import { SkipLink } from "./SkipLink";
import { TopBar } from "./TopBar";
import { useViewportClass } from "./useViewportClass";

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
 * Top-level layout of the PlumeTrace page: the control room on desktop, the light mobile page
 * (no data, no 3D) on phones and small touch screens (see {@link useViewportClass}).
 *
 * @returns The application shell.
 */
export function AppShell(): JSX.Element {
  return useViewportClass() === "mobile" ? <MobilePage /> : <ControlRoom />;
}

/**
 * The PlumeTrace control room (desktop, 1280 px and wider).
 *
 * Rows: top bar 48 px, working area, trends 220 px, playback bar 44 px. The working area has
 * the tabbed left column (Alarms and Equipment, 320 px), the station view (the 3D scene or its
 * still-image fallback) and the station log (360 px). The load status sits above the 3D canvas,
 * on its own solid surface. Below 1280 px the log moves under the left column. It mounts the data
 * bootstrap, the playback clock loop and the keyboard shortcuts once, and starts with a skip link.
 * The "Simulated" label is always visible because every station value is simulated (design
 * section 8).
 *
 * @returns The control room.
 */
function ControlRoom(): JSX.Element {
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
      <SkipLink />
      <TopBar mode={mode} />
      <div className="grid min-h-0 grid-cols-[320px_minmax(0,1fr)] grid-rows-2 min-[1280px]:grid-cols-[320px_minmax(0,1fr)_360px] min-[1280px]:grid-rows-1">
        <div className="col-start-1 row-start-1 grid min-h-0 grid-rows-[minmax(0,1fr)]">
          <LeftColumn scenario={scenario} />
        </div>
        <main
          aria-label="Station view"
          className="relative col-start-2 row-span-2 row-start-1 flex min-h-0 items-center justify-center p-6 min-[1280px]:row-span-1"
        >
          <div className="absolute inset-0">
            <StationView />
          </div>
          <div className="relative z-10 border border-border-2 bg-surface-1 p-4 empty:hidden">
            <StationStatus mode={mode} />
          </div>
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
