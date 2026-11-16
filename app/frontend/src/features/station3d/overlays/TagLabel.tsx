import { Html } from "@react-three/drei";
import { useMemo, type JSX } from "react";

import { useSelectionStore } from "@/shared/selection";
import type { FacilitySpec } from "@/shared/types/generated/contract";

import { tagBounds, type NodeIndex } from "../model/nodeIndex";
import { overlayTags } from "./overlayTags";
import { describeTag, labelPosition } from "./tagLabelText";

interface LabelProps {
  tag: string | null;
  index: NodeIndex;
  spec: FacilitySpec;
}

/** One label above the top centre of the tag box; nothing for a null or unknown tag. */
function Label({ tag, index, spec }: LabelProps): JSX.Element | null {
  const position = useMemo(() => {
    const bounds = tag === null ? null : tagBounds(tag, index, spec);
    return bounds === null ? null : labelPosition(bounds);
  }, [tag, index, spec]);
  if (tag === null || position === null) return null;
  return (
    <Html position={position} center pointerEvents="none" zIndexRange={[20, 0]}>
      <div className="flex items-baseline gap-2 border border-border-2 bg-surface-1/90 px-2 py-1 text-xs whitespace-nowrap text-text-1">
        <span className="font-mono text-xs">{tag}</span>
        <span className="text-text-2">{describeTag(tag, spec)}</span>
      </div>
    </Html>
  );
}

/**
 * At most two DOM labels: one for the hovered tag and one for the selected tag (tag and type
 * name only; no rate or value). They ignore the pointer, so they never block picking. The choice
 * of tags is `overlayTags`, the text is `describeTag`; the drei `Html` element itself is not
 * rendered in unit tests (the test renderer has no DOM layer), so it is checked in the browser.
 *
 * @param props - `index` and `spec` of the station.
 * @returns The labels.
 */
export function TagLabel({ index, spec }: { index: NodeIndex; spec: FacilitySpec }): JSX.Element {
  const selected = useSelectionStore((s) => s.selectedTag);
  const hovered = useSelectionStore((s) => s.hoveredTag);
  const tags = overlayTags(hovered, selected);
  return (
    <>
      <Label tag={tags.hover} index={index} spec={spec} />
      <Label tag={tags.selected} index={index} spec={spec} />
    </>
  );
}
