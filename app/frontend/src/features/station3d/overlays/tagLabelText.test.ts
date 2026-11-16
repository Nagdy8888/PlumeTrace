import { describe, expect, it } from "vitest";

import { FACILITY } from "../model/facility";
import { EQUIPMENT_LABEL, INSTRUMENT_LABEL, describeTag, labelPosition } from "./tagLabelText";

describe("describeTag", () => {
  it("names equipment by type and instruments by kind", () => {
    expect(describeTag("K-202", FACILITY)).toBe("Recip compressor");
    expect(describeTag("E-231", FACILITY)).toBe("Fin-fan cooler");
    expect(describeTag("AT-101", FACILITY)).toBe("Methane sensor");
  });

  it("returns an empty name for an unknown tag", () => {
    expect(describeTag("NOPE-1", FACILITY)).toBe("");
  });

  it("has a distinct English name for each of the 15 equipment types and 6 instrument kinds", () => {
    expect(new Set(Object.values(EQUIPMENT_LABEL)).size).toBe(15);
    expect(new Set(Object.values(INSTRUMENT_LABEL)).size).toBe(6);
  });

  it("gives every equipment item and every instrument of the facility a name", () => {
    for (const e of FACILITY.equipment) expect(describeTag(e.tag, FACILITY), e.tag).not.toBe("");
    for (const i of FACILITY.instruments) expect(describeTag(i.tag, FACILITY), i.tag).not.toBe("");
  });
});

describe("labelPosition", () => {
  it("is the top centre of the box, 1 m above it", () => {
    expect(labelPosition({ min: [8, 0, -21], max: [12, 6, -19] })).toEqual([10, 7, -20]);
  });
});
