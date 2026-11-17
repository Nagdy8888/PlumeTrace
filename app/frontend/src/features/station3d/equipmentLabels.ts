import type { EquipmentType, InstrumentKind } from "@/shared/types/generated/contract";

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

/** Name of the group that holds the eight fence-line methane sensors. */
export const SENSOR_AREA = "Methane sensors";

/** Areas of the station in the fixed order the equipment list shows them. */
export const AREA_ORDER = [
  "Inlet",
  "Compression",
  "Dehydration",
  "Fuel gas",
  "Storage",
  "Flare",
  "Metering and outlet",
  "Buildings",
  SENSOR_AREA,
] as const;

/** One entry of {@link AREA_ORDER}. */
export type Area = (typeof AREA_ORDER)[number];

/** Area of each equipment tag of the facility spec (the sensors form the {@link SENSOR_AREA} group). */
export const AREA_OF_TAG: Record<string, Area> = {
  "PIG-101": "Inlet",
  "V-100": "Inlet",
  "V-211": "Compression",
  "V-212": "Compression",
  "V-213": "Compression",
  "K-201": "Compression",
  "K-202": "Compression",
  "K-203": "Compression",
  "E-231": "Compression",
  "E-232": "Compression",
  "E-233": "Compression",
  "VS-250": "Compression",
  "T-301": "Dehydration",
  "R-302": "Dehydration",
  "FG-501": "Fuel gas",
  "TK-401": "Storage",
  "TK-402": "Storage",
  "VRU-410": "Storage",
  "V-602": "Flare",
  "FL-601": "Flare",
  "M-701": "Metering and outlet",
  "PIG-702": "Metering and outlet",
  "CR-901": "Buildings",
  "MCC-902": "Buildings",
};
