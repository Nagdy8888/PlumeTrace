import type { JSX } from "react";

import { useActiveScenario } from "@/shared/data";

/** The five legend steps: concentration label and the ramp token that colours it (log scale). */
const STEPS = [
  { label: "1", token: "--ch4-0" },
  { label: "3", token: "--ch4-1" },
  { label: "10", token: "--ch4-2" },
  { label: "30", token: "--ch4-3" },
  { label: "100+", token: "--ch4-4" },
] as const;

/**
 * Colour key of the plume heat-map, bottom-left of the station area (a solid panel, not over the
 * scene). It states the unit and what the picture is: the output of the dispersion model, not a
 * measurement; methane itself is invisible. Hidden while no scenario is loaded. It shows
 * concentrations only, never an emission rate.
 *
 * @returns The legend, or nothing without a scenario.
 */
export function PlumeLegend(): JSX.Element | null {
  const scenario = useActiveScenario();
  if (scenario === null) return null;
  return (
    <div
      role="group"
      aria-labelledby="plume-legend-title"
      className="absolute bottom-3 left-3 z-10 w-64 border border-border-2 bg-surface-1 p-3 text-xs"
    >
      <div id="plume-legend-title" className="text-text-1">
        Methane above background, ppm (model at 1.5 m)
      </div>
      <ul className="mt-2 grid grid-cols-5 gap-1">
        {STEPS.map(({ label, token }) => (
          <li key={label} className="flex flex-col gap-1">
            <span className="block h-3 border border-border-2" style={{ backgroundColor: `var(${token})` }} />
            <span className="font-mono text-text-1">{label}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-text-2">Visualisation of the dispersion model. Methane is invisible.</p>
    </div>
  );
}
