import { lazy, Suspense, type JSX } from "react";

/** r3f-perf is a dev dependency: it is imported dynamically and only when `import.meta.env.DEV`. */
const Perf = import.meta.env.DEV
  ? lazy(() => import("r3f-perf").then((m) => ({ default: m.Perf })))
  : null;

/**
 * Frame-rate, draw-call and triangle overlay for measuring the 3D budget (dev builds, `?perf`).
 *
 * @returns The overlay, or nothing outside dev builds.
 */
export function PerfOverlay(): JSX.Element | null {
  if (Perf === null) return null;
  return (
    <Suspense fallback={null}>
      <Perf position="top-left" />
    </Suspense>
  );
}
