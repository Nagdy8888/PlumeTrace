import type { EquipmentType, FacilitySpec, InstrumentKind } from "@/shared/types/generated/contract";

import type { Vec3 } from "../interaction/flyToTarget";

/** English names of the 15 equipment types. */
export const EQUIPMENT_LABEL: Record<EquipmentType, string> = {
  pig_trap: "Pig trap",
  filter_separator: "Filter separator",
  scrubber: "Scrubber",
  recip_compressor: "Recip compressor",
  fin_fan_cooler: "Fin-fan cooler",
  vent_stack: "Vent stack",
  teg_contactor: "TEG contactor",
  teg_regenerator: "TEG regenerator",
  fuel_gas_skid: "Fuel gas skid",
  storage_tank: "Storage tank",
  vru: "Vapour recovery unit",
  knockout_drum: "Knockout drum",
  flare_stack: "Flare stack",
  meter_run: "Meter run",
  building: "Building",
};

/** English names of the instrument kinds. */
export const INSTRUMENT_LABEL: Record<InstrumentKind, string> = {
  methane_point: "Methane sensor",
  met_mast: "Met mast",
  flow: "Flow meter",
  temperature: "Temperature sensor",
  pressure: "Pressure sensor",
  thermocouple: "Thermocouple",
};

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
