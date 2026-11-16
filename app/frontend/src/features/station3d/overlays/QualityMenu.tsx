import type { JSX } from "react";

import { QUALITY, type QualityTier } from "../scene/qualitySettings";
import { requestResetView, useStationStore, type QualityOverride } from "../store";

const TIERS = Object.keys(QUALITY) as QualityTier[];

function label(tier: QualityTier): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

function isOverride(value: string): value is QualityOverride {
  return value === "auto" || (TIERS as string[]).includes(value);
}

/**
 * Controls over the 3D view, in the corner of the station area: a native quality select (Auto
 * follows the frame-rate monitor and shows the tier it picked) and a `Reset view` button that
 * flies back to the review camera. Both controls show their purpose in text (`Quality`, and the
 * `R` key next to `Reset view`) so the shortcut is learnable from the button.
 *
 * @returns The control group.
 */
export function QualityMenu(): JSX.Element {
  const override = useStationStore((s) => s.override);
  const autoTier = useStationStore((s) => s.autoTier);
  const setOverride = useStationStore((s) => s.setOverride);
  return (
    <div className="absolute top-3 right-3 z-10 flex items-center gap-2 text-xs">
      <button
        type="button"
        onClick={requestResetView}
        aria-label="Reset view"
        aria-keyshortcuts="R"
        className="flex h-7 items-center gap-2 rounded-sm border border-border-2 bg-surface-2 px-2 text-xs text-text-1 hover:bg-surface-3"
      >
        Reset view
        <kbd aria-hidden="true" className="font-mono text-text-2">
          R
        </kbd>
      </button>
      <div className="flex h-7 items-center rounded-sm border border-border-2 bg-surface-2 pl-2">
        <span aria-hidden="true" className="text-text-2">
          Quality
        </span>
        <select
          aria-label="3D quality"
          value={override}
          onChange={(e) => isOverride(e.target.value) && setOverride(e.target.value)}
          className="h-full bg-surface-2 px-2 text-xs text-text-1"
        >
          <option value="auto">{`Auto (${label(autoTier)})`}</option>
          {TIERS.map((tier) => (
            <option key={tier} value={tier}>
              {label(tier)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
