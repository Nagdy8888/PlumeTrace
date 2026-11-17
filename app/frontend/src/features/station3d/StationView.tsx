import { lazy, Suspense, type JSX } from "react";

import { QualityMenu } from "./overlays/QualityMenu";
import { PlumeLegend } from "./plume/PlumeLegend";

const StationCanvas = lazy(() => import("./StationCanvas"));

/** True when the browser has WebGL 2 (jsdom and old browsers do not; the full fallback is Task 10). */
const HAS_WEBGL = typeof WebGL2RenderingContext !== "undefined";

/**
 * The 3D station view: the lazily loaded canvas (so the 2D panels render first), the quality
 * menu in the top corner and the plume legend in the bottom corner. Names missing from the model are logged by the scene with
 * `console.error("station model is missing nodes", ...)`.
 *
 * @returns The canvas, menu and legend, or nothing when WebGL 2 is unavailable.
 */
export function StationView(): JSX.Element | null {
  if (!HAS_WEBGL) return null;
  return (
    <>
      <Suspense fallback={null}>
        <StationCanvas />
      </Suspense>
      <QualityMenu />
      <PlumeLegend />
    </>
  );
}
