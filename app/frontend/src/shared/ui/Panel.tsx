import { useId, type JSX, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

/** Props of {@link Panel}. */
export interface PanelProps {
  /** Header text; also the accessible name of the region. */
  title: string;
  /** Optional controls shown at the right end of the header row. */
  actions?: ReactNode;
  /** Panel body; it scrolls when taller than the panel. */
  children: ReactNode;
  /** Extra classes for the outer section (layout only). */
  className?: string;
}

/**
 * Bordered working surface with a 32 px header row, the container of every control-room panel.
 *
 * @param props - See {@link PanelProps}.
 * @returns A labelled `<section>` region.
 */
export function Panel({ title, actions, children, className }: PanelProps): JSX.Element {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className={cn("flex min-h-0 flex-col rounded-sm border border-border-1 bg-surface-1", className)}
    >
      <header className="flex h-8 shrink-0 items-center justify-between gap-2 border-b border-border-1 px-3">
        <h2 id={titleId} className="truncate text-sm font-medium text-text-2">
          {title}
        </h2>
        {actions ? <div className="flex items-center gap-1">{actions}</div> : null}
      </header>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}
