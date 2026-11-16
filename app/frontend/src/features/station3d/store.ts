import { create } from "zustand";

import type { QualityTier } from "./scene/qualitySettings";

/** `localStorage` key of the manual quality override. */
const STORAGE_KEY = "plumetrace.quality";

/** The manual choice in the quality menu: a fixed tier, or `auto` (the frame-rate monitor decides). */
export type QualityOverride = QualityTier | "auto";

/** State and actions of the 3D view: quality tier and reduced-motion preference. */
export interface StationState {
  /** Manual choice; `auto` lets `autoTier` decide. */
  override: QualityOverride;
  /** Tier chosen by the frame-rate monitor; starts at `high`. */
  autoTier: QualityTier;
  /** True when the OS asks for reduced motion. */
  reducedMotion: boolean;
  /** Drop the automatic tier one step (`high`, `medium`, `low`); it stays at `low`. */
  decline: () => void;
  /** Set the manual choice and remember it in `localStorage` (a storage error is ignored). */
  setOverride: (value: QualityOverride) => void;
  /** Set the reduced-motion flag. */
  setReducedMotion: (value: boolean) => void;
}

const NEXT_LOWER: Record<QualityTier, QualityTier> = { high: "medium", medium: "low", low: "low" };

function isOverride(value: unknown): value is QualityOverride {
  return value === "auto" || value === "high" || value === "medium" || value === "low";
}

function readStoredOverride(): QualityOverride {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isOverride(stored) ? stored : "auto";
  } catch {
    return "auto"; // private window or blocked storage: the page works without it
  }
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Quality tier and motion preference of the 3D station view. */
export const useStationStore = create<StationState>()((set) => ({
  override: readStoredOverride(),
  autoTier: "high",
  reducedMotion: prefersReducedMotion(),
  decline: () => set((s) => ({ autoTier: NEXT_LOWER[s.autoTier] })),
  setOverride: (value) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // not persisted; the choice still applies for this visit
    }
    set({ override: value });
  },
  setReducedMotion: (value) => set({ reducedMotion: value }),
}));

if (typeof window.matchMedia === "function") {
  window
    .matchMedia("(prefers-reduced-motion: reduce)")
    .addEventListener("change", (event) => useStationStore.getState().setReducedMotion(event.matches));
}

/**
 * The tier in force: the manual choice, or the automatic tier when the choice is `auto`.
 *
 * @returns The tier the canvas renders at.
 */
export function useQualityTier(): QualityTier {
  return useStationStore((s) => (s.override === "auto" ? s.autoTier : s.override));
}

/** Name of the window event that asks the 3D view to return to the review camera. */
export const RESET_VIEW_EVENT = "plumetrace:reset-view";

/** Ask the 3D view to fly back to the review camera (the quality menu button, outside the canvas). */
export function requestResetView(): void {
  window.dispatchEvent(new Event(RESET_VIEW_EVENT));
}
