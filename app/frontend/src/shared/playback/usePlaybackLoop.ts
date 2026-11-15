import { useEffect } from "react";

import { useClockStore } from "./clockStore";

/**
 * Drive the clock with one `requestAnimationFrame` loop.
 *
 * Mount it once (in `AppShell`). Each frame calls `tick(dt / 1000)` with the time since the
 * previous frame; the first frame only records the timestamp. It holds no React state and
 * cancels the loop on unmount.
 */
export function usePlaybackLoop(): void {
  useEffect(() => {
    let frame = 0;
    let last: number | null = null;
    const step = (now: number): void => {
      if (last !== null) useClockStore.getState().tick((now - last) / 1000);
      last = now;
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, []);
}
