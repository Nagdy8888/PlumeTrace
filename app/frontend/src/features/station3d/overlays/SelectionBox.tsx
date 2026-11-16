import { useMemo, type JSX } from "react";
import { BoxGeometry, EdgesGeometry } from "three";

import { useSelectionStore } from "@/shared/selection";
import type { FacilitySpec } from "@/shared/types/generated/contract";

import { tagBounds, type NodeIndex } from "../model/nodeIndex";
import { overlayTags } from "./overlayTags";

/** The edges of one unit box, shared by both outlines and scaled per tag. */
const UNIT_EDGES = new EdgesGeometry(new BoxGeometry(1, 1, 1));
const OUTLINE_ORDER = 10;
const HOVER_OPACITY = 0.5;
/** Colour used only when a design token cannot be read (a test without the stylesheet). */
const TOKEN_FALLBACK = "#ffffff";

type Vec3 = [number, number, number];

/** Read a colour token from the page once; the 3D layer has no second palette. */
function readToken(name: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value === "" ? TOKEN_FALLBACK : value;
}

interface OutlineProps {
  tag: string | null;
  index: NodeIndex;
  spec: FacilitySpec;
  color: string;
  opacity: number;
}

/** One outline that is always mounted and toggled with `visible`. */
function Outline({ tag, index, spec, color, opacity }: OutlineProps): JSX.Element {
  const bounds = useMemo(() => (tag === null ? null : tagBounds(tag, index, spec)), [tag, index, spec]);
  const placement = useMemo((): { position: Vec3; scale: Vec3 } => {
    if (bounds === null) return { position: [0, 0, 0], scale: [1, 1, 1] };
    const { min, max } = bounds;
    return {
      position: [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2],
      scale: [max[0] - min[0], max[1] - min[1], max[2] - min[2]],
    };
  }, [bounds]);
  return (
    <lineSegments
      geometry={UNIT_EDGES}
      visible={bounds !== null}
      position={placement.position}
      scale={placement.scale}
      renderOrder={OUTLINE_ORDER}
      raycast={() => undefined}
    >
      <lineBasicMaterial color={color} depthTest={false} transparent opacity={opacity} />
    </lineSegments>
  );
}

/**
 * Box outline of the selected tag (accent colour) and of the hovered tag (text-2 at half
 * opacity). Both lines are always mounted and shown with `visible`, drawn over the model
 * (`depthTest` off). Colours are read once from the CSS tokens `--accent` and `--text-2`.
 *
 * @param props - `index` and `spec` of the station.
 * @returns The two outlines.
 */
export function SelectionBox({ index, spec }: { index: NodeIndex; spec: FacilitySpec }): JSX.Element {
  const selected = useSelectionStore((s) => s.selectedTag);
  const hovered = useSelectionStore((s) => s.hoveredTag);
  const accent = useMemo(() => readToken("--accent"), []);
  const muted = useMemo(() => readToken("--text-2"), []);
  const tags = overlayTags(hovered, selected);
  return (
    <>
      <Outline tag={tags.hover} index={index} spec={spec} color={muted} opacity={HOVER_OPACITY} />
      <Outline tag={tags.selected} index={index} spec={spec} color={accent} opacity={1} />
    </>
  );
}
