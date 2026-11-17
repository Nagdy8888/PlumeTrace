import { Html } from "@react-three/drei";
import { useMemo, type JSX } from "react";
import { SphereGeometry, Vector3 } from "three";

import { useNodeIndex } from "../model/nodeIndex";
import { readTokenColor } from "../plume/plumeColors";

/** One emission candidate from the inversion tool result (Phase 5 supplies them). */
export interface Candidate {
  /** Anchor id of the candidate, for example `VS-250.tip`. */
  anchorId: string;
  /** Label for the top candidate. */
  label: string;
  /** Posterior probability, 0 to 1; it sets the glow strength. */
  probability: number;
}

const RADIUS_M = 0.6;
const sphere = new SphereGeometry(RADIUS_M, 24, 16);

/**
 * Glow strength for a probability: `1 + 3 * p`, so a certain candidate glows four times the base.
 *
 * @param probability - Posterior probability, 0 to 1.
 * @returns The emissive intensity.
 */
function glowFor(probability: number): number {
  return 1 + 3 * probability;
}

/**
 * Highlights the inversion's candidate sources: a glowing sphere at each known anchor whose
 * strength follows the probability, and a label on the top candidate only
 * (`<label> <probability as integer %>`, text from the props alone). A candidate with an unknown
 * anchor is skipped. Colour is the `--candidate` token; the sphere is not tone mapped so it passes
 * the bloom threshold.
 *
 * Built and tested in Phase 4 Task 9 but NOT mounted anywhere. It is not R3-compliant until
 * Phase 5 adds the fixed "model probability" label and the benchmark link before mounting it.
 *
 * @param props - `candidates` from the inversion result; `labels` false hides the DOM label
 * (the test renderer has no DOM layer).
 * @returns The spheres and the top label.
 */
export function CandidateHighlight({
  candidates,
  labels = true,
}: {
  candidates: readonly Candidate[];
  labels?: boolean;
}): JSX.Element {
  const index = useNodeIndex();
  const colour = useMemo(() => readTokenColor("--candidate"), []);
  const placed = useMemo(
    () =>
      candidates.flatMap((c) => {
        const node = index.get(c.anchorId);
        return node === undefined ? [] : [{ ...c, position: node.getWorldPosition(new Vector3()).toArray() }];
      }),
    [candidates, index],
  );
  const top = placed.reduce<(typeof placed)[number] | null>(
    (best, c) => (best === null || c.probability > best.probability ? c : best),
    null,
  );
  return (
    <>
      {placed.map((c) => (
        <mesh key={c.anchorId} name={`candidate-${c.anchorId}`} geometry={sphere} position={c.position} raycast={() => undefined}>
          <meshStandardMaterial color={colour} emissive={colour} emissiveIntensity={glowFor(c.probability)} toneMapped={false} />
          {labels && c === top && (
            <Html center pointerEvents="none" position={[0, RADIUS_M + 0.6, 0]}>
              <div className="border border-border-2 bg-surface-1 px-2 py-1 text-xs whitespace-nowrap text-text-1">{`${c.label} ${Math.round(c.probability * 100)}%`}</div>
            </Html>
          )}
        </mesh>
      ))}
    </>
  );
}
