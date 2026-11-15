import { lazy, Suspense, type JSX } from "react";

const StationCanvas = lazy(() => import("./StationCanvas"));

/** True when the browser has WebGL 2 (jsdom and old browsers do not; the full fallback is Task 10). */
const HAS_WEBGL = typeof WebGL2RenderingContext !== "undefined";

/**
 * The 3D station view. The canvas is loaded lazily so the 2D panels render first.
 *
 * @returns The lazily loaded canvas, or nothing when WebGL 2 is unavailable.
 */
export function StationView(): JSX.Element | null {
  if (!HAS_WEBGL) return null;
  return (
    <Suspense fallback={null}>
      <StationCanvas />
    </Suspense>
  );
}
