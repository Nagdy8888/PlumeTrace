import { useSyncExternalStore } from "react";

/** Which layout the page uses: the full control room, or the light page without 3D. */
export type ViewportClass = "mobile" | "desktop";

const NARROW = "(max-width: 767px)";
const COARSE = "(pointer: coarse)";
const COARSE_MAX_WIDTH_PX = 1024;

function matches(query: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

function current(): ViewportClass {
  return matches(NARROW) || (matches(COARSE) && window.innerWidth < COARSE_MAX_WIDTH_PX) ? "mobile" : "desktop";
}

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const lists = [NARROW, COARSE].map((q) => window.matchMedia(q));
  for (const list of lists) list.addEventListener("change", onChange);
  window.addEventListener("resize", onChange);
  return () => {
    for (const list of lists) list.removeEventListener("change", onChange);
    window.removeEventListener("resize", onChange);
  };
}

/**
 * The layout class of this device: `mobile` when the screen is narrower than 768 px, or when the
 * pointer is coarse and the window is narrower than 1024 px; otherwise `desktop`. A large touch
 * screen (a laptop with touch, a tablet in landscape at 1024 px or more) keeps the control room.
 * Updates when the media queries or the window size change; without `matchMedia` it is `desktop`.
 *
 * @returns `"mobile"` or `"desktop"`.
 */
export function useViewportClass(): ViewportClass {
  return useSyncExternalStore(subscribe, current, () => "desktop");
}
