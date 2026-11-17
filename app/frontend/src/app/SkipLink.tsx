import type { JSX } from "react";

/**
 * The first focusable element of the page: a link that jumps past the top bar to the alarms
 * (`#alarms-panel`). It is visually hidden until it has keyboard focus, then shown at the top left
 * on a solid surface.
 *
 * @returns The skip link.
 */
export function SkipLink(): JSX.Element {
  return (
    <a
      href="#alarms-panel"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:border focus:border-border-2 focus:bg-surface-2 focus:px-3 focus:py-2 focus:text-sm focus:text-text-1"
    >
      Skip to alarms
    </a>
  );
}
