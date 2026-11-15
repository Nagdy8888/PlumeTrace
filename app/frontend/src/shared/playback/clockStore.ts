import { create } from "zustand";

/** Playback speeds: simulated seconds per real second. */
export const SPEEDS = [1, 10, 60, 120] as const;

/** One of the allowed playback speeds. */
export type Speed = (typeof SPEEDS)[number];

/** Speed on load: one simulated minute per real second. */
export const DEFAULT_SPEED: Speed = 60;

/** Length of one replay sample in simulated seconds (the file's `step_s`). */
export const SAMPLE_STEP_S = 60;

/** State and actions of the simulation clock. */
export interface ClockState {
  /** Simulation time in seconds since the scenario start. */
  tSeconds: number;
  /** Scenario length in seconds; 0 while no scenario is loaded. */
  durationS: number;
  /** Whether the clock advances on `tick`. */
  playing: boolean;
  /** Simulated seconds per real second. */
  speed: Speed;
  /** Start playing; no-op on an empty timeline; at the end it restarts from 0. */
  play: () => void;
  /** Stop advancing. */
  pause: () => void;
  /** Change the playback speed. */
  setSpeed: (speed: Speed) => void;
  /** Jump to `t` seconds, clamped to `[0, durationS]` (a non-finite value is ignored). */
  seek: (t: number) => void;
  /** Load a new timeline: `t = 0`, paused, speed unchanged. */
  reset: (durationS: number) => void;
  /**
   * Advance by `dtRealS` real seconds times the speed. Ignores a step that is not in `(0, 1]`
   * (a tab that slept must not jump); stops at the end.
   */
  tick: (dtRealS: number) => void;
}

/**
 * The single time source of the app. Panels read the sample index (`useSampleIndex`); the 3D layer
 * reads `useClockStore.getState()` inside `useFrame`. Nothing else keeps its own clock.
 */
export const useClockStore = create<ClockState>()((set, get) => ({
  tSeconds: 0,
  durationS: 0,
  playing: false,
  speed: DEFAULT_SPEED,
  play: () => {
    const { durationS, tSeconds } = get();
    if (durationS === 0) return;
    set({ playing: true, tSeconds: tSeconds >= durationS ? 0 : tSeconds });
  },
  pause: () => set({ playing: false }),
  setSpeed: (speed) => set({ speed }),
  seek: (t) => {
    if (!Number.isFinite(t)) return;
    set({ tSeconds: Math.min(Math.max(t, 0), get().durationS) });
  },
  reset: (durationS) => set({ tSeconds: 0, durationS, playing: false }),
  tick: (dtRealS) => {
    const { playing, tSeconds, durationS, speed } = get();
    if (!playing || !(dtRealS > 0) || dtRealS > 1) return;
    const next = Math.min(durationS, tSeconds + dtRealS * speed);
    set({ tSeconds: next, playing: next < durationS });
  },
}));

/** Index of the 60 s sample at clock time `t`, clamped to the timeline. */
function sampleIndexOf(s: ClockState): number {
  const n = Math.max(1, Math.round(s.durationS / SAMPLE_STEP_S));
  return Math.max(0, Math.min(n - 1, Math.floor(s.tSeconds / SAMPLE_STEP_S)));
}

/**
 * Index of the current 60 s sample.
 *
 * The selector returns a number, so a component re-renders only when the index changes (once per
 * simulated minute), never per animation frame.
 *
 * @returns The sample index, `0` to `n - 1` (`n = max(1, round(durationS / 60))`).
 */
export function useSampleIndex(): number {
  return useClockStore(sampleIndexOf);
}
