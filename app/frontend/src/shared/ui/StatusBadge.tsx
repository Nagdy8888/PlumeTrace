import type { JSX, ReactNode } from "react";

/** Severity or state of a {@link StatusBadge}. */
export type StatusTone = "high" | "med" | "low" | "ok" | "neutral";

/** Props of {@link StatusBadge}. */
export interface StatusBadgeProps {
  /** Meaning of the badge; picks the marker colour. */
  tone: StatusTone;
  /** The text label; it always carries the meaning, the colour only reinforces it. */
  children: ReactNode;
}

const MARKER: Record<StatusTone, string> = {
  high: "bg-alarm-high",
  med: "bg-alarm-med",
  low: "bg-alarm-low",
  ok: "bg-ok",
  neutral: "bg-text-3",
};

/**
 * Text label with a 6 px square marker in the tone colour; never colour alone.
 *
 * @param props - See {@link StatusBadgeProps}.
 * @returns An inline status label.
 */
export function StatusBadge({ tone, children }: StatusBadgeProps): JSX.Element {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-text-1">
      <span aria-hidden="true" className={`size-1.5 shrink-0 ${MARKER[tone]}`} />
      {children}
    </span>
  );
}
