import { useEffect, useMemo, type JSX, type ReactNode } from "react";
import type { Object3D } from "three";

import { useActiveScenario } from "@/shared/data";
import type { FacilitySpec } from "@/shared/types/generated/contract";

import { FlareFlame } from "../overlays/FlareFlame";
import { SensorMarkers } from "../overlays/SensorMarkers";
import { WindSock } from "../overlays/WindSock";
import { PlumeLayer } from "../plume/PlumeLayer";
import { SelectionBox } from "../overlays/SelectionBox";
import { TagLabel } from "../overlays/TagLabel";
import { AnimatedParts } from "./AnimatedParts";
import { HitProxies } from "./HitProxies";
import { buildNodeIndex, NodeIndexContext } from "./nodeIndex";

/** Props of {@link StationScene}. */
export interface StationSceneProps {
  /** Loaded (glb) or procedurally built station root; it must have an identity transform. */
  root: Object3D;
  /** Facility spec: tags, anchors and instruments. */
  spec: FacilitySpec;
  /** Show the hover and selection labels (they need a DOM; the test renderer has none). Default true. */
  labels?: boolean;
  /** Extra scene content that reads the node index through {@link useNodeIndex}. */
  children?: ReactNode;
}

/** Missing-name lists already reported, so StrictMode and re-renders log once. */
const reported = new Set<string>();

function reportMissing(missing: readonly string[]): void {
  const key = missing.join("|");
  if (missing.length === 0 || reported.has(key)) return;
  reported.add(key);
  console.error("station model is missing nodes", missing);
}

/**
 * The station as the real-time layer sees it: the model, its node index (also published through
 * {@link NodeIndexContext}), the picking proxies, the animated fans, the selection outline, the
 * labels and, for the loaded scenario, the plume, the sensor markers and the windsock, plus the
 * flare flame. Names missing from the model are logged once with `console.error`.
 *
 * @param props - See {@link StationSceneProps}.
 * @returns The scene content.
 */
export function StationScene({ root, spec, labels = true, children }: StationSceneProps): JSX.Element {
  const index = useMemo(() => buildNodeIndex(root, spec), [root, spec]);
  useEffect(() => reportMissing(index.missing), [index]);
  const scenario = useActiveScenario();
  return (
    <NodeIndexContext.Provider value={index}>
      <primitive object={root} dispose={null} />
      <HitProxies index={index} />
      <AnimatedParts index={index} />
      <SelectionBox index={index} spec={spec} />
      {labels && <TagLabel index={index} spec={spec} />}
      {scenario !== null && <PlumeLayer scenario={scenario} />}
      {scenario !== null && <SensorMarkers scenario={scenario} />}
      <WindSock scenario={scenario} />
      <FlareFlame />
      {children}
    </NodeIndexContext.Provider>
  );
}
