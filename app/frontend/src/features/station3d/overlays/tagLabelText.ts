import type { FacilitySpec } from "@/shared/types/generated/contract";

import { EQUIPMENT_LABEL, INSTRUMENT_LABEL } from "../equipmentLabels";
import type { Vec3 } from "../interaction/flyToTarget";

// The name maps moved to `equipmentLabels.ts` (shared with the equipment list); re-exported here.
export { EQUIPMENT_LABEL, INSTRUMENT_LABEL };

/** Height of the label above the top of the box, in metres. */
const LABEL_LIFT_M = 1;

/**
 * Type name shown next to a tag: the equipment type, or the instrument kind.
 *
 * @param tag - Equipment tag or instrument tag.
 * @param spec - Facility spec.
 * @returns The English name, or an empty string for an unknown tag.
 */
export function describeTag(tag: string, spec: FacilitySpec): string {
  const equipment = spec.equipment.find((e) => e.tag === tag);
  if (equipment !== undefined) return EQUIPMENT_LABEL[equipment.type];
  const instrument = spec.instruments.find((i) => i.tag === tag);
  return instrument === undefined ? "" : INSTRUMENT_LABEL[instrument.kind];
}

/**
 * Where a label sits: the top centre of the tag box, 1 m above it.
 *
 * @param bounds - Box of the tag in scene coordinates.
 * @returns The label position in scene coordinates.
 */
export function labelPosition(bounds: { min: Vec3; max: Vec3 }): Vec3 {
  const { min, max } = bounds;
  return [(min[0] + max[0]) / 2, max[1] + LABEL_LIFT_M, (min[2] + max[2]) / 2];
}
