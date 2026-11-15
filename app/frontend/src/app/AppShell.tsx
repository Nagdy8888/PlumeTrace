import type { JSX } from "react";

/**
 * Top-level layout of the PlumeTrace control room.
 *
 * Phase 1 renders only the top bar and an empty station region; later phases fill the
 * station view, panels and trends. The "Simulated" label is always visible because every
 * station value is simulated (design section 8).
 *
 * @returns The application shell.
 */
export function AppShell(): JSX.Element {
  return (
    <div className="flex h-full flex-col bg-surface-0 text-text-1">
      <header className="flex items-center justify-between border-b border-border-1 px-4 py-2">
        <h1 className="text-base font-semibold">PlumeTrace</h1>
        <span className="rounded-sm border border-border-2 px-2 py-0.5 text-xs text-text-2">
          Simulated
        </span>
      </header>
      <main aria-label="Station view" className="flex-1" />
    </div>
  );
}
