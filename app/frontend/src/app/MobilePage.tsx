import type { JSX } from "react";

import { STATION_IMAGE_ALT, STATION_IMAGE_SRC } from "@/features/station3d";

/**
 * The light page for phones and small touch screens, shown instead of the control room: product
 * name and the always-visible "Simulated" label, what the replay shows, a still image of the
 * station and the hint to open the page on a desktop. It loads no scenario data and never imports
 * the 3D scene. The demo video arrives here in Phase 7 (planned, not built).
 *
 * @returns The mobile page.
 */
export function MobilePage(): JSX.Element {
  return (
    <div className="min-h-full bg-surface-0 text-text-1">
      <header className="flex h-12 items-center justify-between border-b border-border-1 bg-surface-1 px-4">
        <span className="text-md font-semibold">PlumeTrace</span>
        <span className="rounded-sm border border-border-2 px-2 py-0.5 text-xs text-text-2">Simulated</span>
      </header>
      <main className="mx-auto flex max-w-xl flex-col gap-4 px-4 py-6">
        <h1 className="text-lg font-semibold text-balance">Methane leak detection for a simulated compressor station</h1>
        <p className="text-base text-text-2">
          PlumeTrace replays simulated leak scenarios from eight fence-line methane sensors at the fictional Station
          KS-07: methane rises, alarms, wind and a dispersion-model view of the plume.
        </p>
        <img
          src={STATION_IMAGE_SRC}
          alt={STATION_IMAGE_ALT}
          width={1920}
          height={1080}
          fetchPriority="high"
          className="h-auto w-full border border-border-1"
        />
        <p className="text-base text-text-1">Open this page in a desktop browser to use the interactive control room.</p>
      </main>
    </div>
  );
}
