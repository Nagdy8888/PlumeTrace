import { describe, expect, it } from "vitest";

import { specToScene } from "./coords";

describe("specToScene", () => {
  it("maps the K-202 origin to three.js axes (x east, y up, -z north)", () => {
    expect(specToScene([75, 75, 0])).toEqual([75, 0, -75]);
  });

  it("maps the VS-250 tip anchor", () => {
    expect(specToScene([85, 115, 12])).toEqual([85, 12, -115]);
  });
});
