import { useSampleIndex } from "@/shared/playback";

import { useActiveScenario } from "./scenarioStore";

/** Met-mast conditions at the current clock sample. */
export interface CurrentConditions {
  /** 60 s mean wind speed in m/s. */
  windSpeed_m_s: number;
  /** 60 s circular mean wind direction in degrees clockwise from north (direction it blows from). */
  windFrom_deg: number;
  /** Pasquill stability class of the sample, `A` to `F`. */
  stability: string;
}

/**
 * Wind and stability of the active scenario at the current 60 s sample.
 *
 * Re-renders once per simulated minute (it reads `useSampleIndex`), never per frame. It returns
 * only the three met-mast fields; it does not expose `keyframes[].sources`.
 *
 * @returns The conditions, or null when no scenario is loaded or the sample is missing.
 */
export function useCurrentConditions(): CurrentConditions | null {
  const scenario = useActiveScenario();
  const i = useSampleIndex();
  const windSpeed = scenario?.wind_speed_m_s[i];
  const windFrom = scenario?.wind_from_deg[i];
  const stability = scenario?.stability[i];
  if (windSpeed === undefined || windFrom === undefined || stability === undefined) return null;
  return { windSpeed_m_s: windSpeed, windFrom_deg: windFrom, stability };
}
