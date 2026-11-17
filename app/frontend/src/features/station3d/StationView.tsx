import { lazy, Suspense, useCallback, useEffect, useRef, useState, type JSX } from "react";

import { StationErrorBoundary } from "./StationErrorBoundary";
import { StationFallback } from "./StationFallback";
import { QualityMenu } from "./overlays/QualityMenu";
import { PlumeLegend } from "./plume/PlumeLegend";
import { hasWebGL2 } from "./webgl";

const StationCanvas = lazy(() => import("./StationCanvas"));

/** A lost graphics context that is not restored within this time switches to the still image. */
const RESTORE_WAIT_MS = 3000;

/**
 * Tracks a lost graphics context: `lost` turns true when the context has been gone for
 * {@link RESTORE_WAIT_MS} without a restore. The loss is logged once with `console.error`.
 */
function useContextLoss(): { lost: boolean; onLost: () => void; onRestored: () => void } {
  const [lost, setLost] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancel = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
  }, []);
  const onLost = useCallback(() => {
    cancel();
    timer.current = setTimeout(() => {
      console.error("station view lost its graphics context and it was not restored");
      setLost(true);
    }, RESTORE_WAIT_MS);
  }, [cancel]);
  useEffect(() => cancel, [cancel]);
  return { lost, onLost, onRestored: cancel };
}

/**
 * The 3D station view: the lazily loaded canvas (so the 2D panels render first), the quality
 * menu in the top corner and the plume legend in the bottom corner. It shows the still image
 * (`StationFallback`) instead when the browser has no WebGL 2 (checked once), when the canvas or
 * the model fails (`StationErrorBoundary`) or when the graphics context is lost and not restored
 * within 3 s. Names missing from the model are logged by the scene with
 * `console.error("station model is missing nodes", ...)`. `?clean` in the URL hides the quality
 * menu and the plume legend; it works in dev builds only (`import.meta.env.DEV`) and is used to
 * take the fallback still.
 *
 * @returns The canvas, menu and legend, or the still image.
 */
export function StationView(): JSX.Element {
  const [webgl] = useState(hasWebGL2);
  const loss = useContextLoss();
  const clean = import.meta.env.DEV && new URLSearchParams(window.location.search).has("clean");
  if (!webgl || loss.lost) return <StationFallback />;
  return (
    <StationErrorBoundary fallback={<StationFallback />}>
      <Suspense fallback={null}>
        <StationCanvas onContextLost={loss.onLost} onContextRestored={loss.onRestored} />
      </Suspense>
      {!clean && <QualityMenu />}
      {!clean && <PlumeLegend />}
    </StationErrorBoundary>
  );
}
