import { describe, expect, it } from "vitest";

import { compass16, formatClock, formatPpm, formatRate, formatUtc } from "./format";

describe("format", () => {
  it("formats ppm with sensible precision", () => {
    expect(formatPpm(4.21)).toBe("4.2 ppm");
    expect(formatPpm(123.4)).toBe("123 ppm");
    expect(formatPpm(null)).toBe("—");
    expect(formatPpm(Number.NaN)).toBe("—");
  });
  it("formats rates", () => {
    expect(formatRate(14.234)).toBe("14.2 kg/h");
    expect(formatRate(null)).toBe("—");
  });
  it("formats simulation time", () => {
    expect(formatUtc("2025-07-15T06:00:00Z", 3725)).toBe("07:02:05 UTC");
    expect(formatClock(7260)).toBe("+02:01");
  });
  it("maps wind direction to 16 compass points", () => {
    expect(compass16(0)).toBe("N");
    expect(compass16(11.24)).toBe("N");
    expect(compass16(11.25)).toBe("NNE");
    expect(compass16(250)).toBe("WSW");
    expect(compass16(359)).toBe("N");
  });
});
