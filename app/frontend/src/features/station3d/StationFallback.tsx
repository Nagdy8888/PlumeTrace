import type { JSX } from "react";

import { STATION_IMAGE_ALT, STATION_IMAGE_SRC } from "./stationImage";

/**
 * Still image of the simulated station, shown instead of the 3D view when WebGL 2 is missing, the
 * model failed to load or the graphics context was lost. The caption says what is missing and
 * what still works.
 *
 * @returns A figure that fills its parent.
 */
export function StationFallback(): JSX.Element {
  return (
    <figure className="absolute inset-0 m-0">
      <img
        src={STATION_IMAGE_SRC}
        alt={STATION_IMAGE_ALT}
        width={1920}
        height={1080}
        className="h-full w-full object-cover"
      />
      <figcaption className="absolute right-3 bottom-3 left-3 border border-border-2 bg-surface-1 px-3 py-2 text-sm text-text-1">
        3D view unavailable on this device. The alarms, equipment list and trends still work.
      </figcaption>
    </figure>
  );
}
