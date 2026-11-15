import type { JSX } from "react";

import type { CurrentConditions } from "@/shared/data";
import { compass16 } from "@/shared/lib/format";

/** Props of {@link WindReadout}. */
export interface WindReadoutProps {
  /** Wind and stability at the current sample, or null when no scenario is loaded. */
  conditions: CurrentConditions | null;
}

/**
 * One-line wind readout: speed, the compass point and degrees it blows from, and stability class.
 *
 * @param props - See {@link WindReadoutProps}.
 * @returns For example `Wind 3.5 m/s from WSW (250°) · Stability D`, or `Wind —` without data.
 */
export function WindReadout({ conditions }: WindReadoutProps): JSX.Element {
  const text =
    conditions === null
      ? "Wind —"
      : `Wind ${conditions.windSpeed_m_s.toFixed(1)} m/s from ${compass16(conditions.windFrom_deg)} (${Math.round(conditions.windFrom_deg)}°) · Stability ${conditions.stability}`;
  return <span className="font-mono text-xs text-text-1">{text}</span>;
}
