import { describe, expect, it } from "vitest";

import { overlayTags } from "./overlayTags";

describe("overlayTags", () => {
  it("returns the hovered and the selected tag when they differ", () => {
    expect(overlayTags("K-201", "K-202")).toEqual({ hover: "K-201", selected: "K-202" });
  });

  it("drops the hover overlay when the hovered tag is the selected one", () => {
    expect(overlayTags("K-202", "K-202")).toEqual({ hover: null, selected: "K-202" });
  });

  it("keeps a hover overlay when nothing is selected, and nothing when both are empty", () => {
    expect(overlayTags("K-201", null)).toEqual({ hover: "K-201", selected: null });
    expect(overlayTags(null, null)).toEqual({ hover: null, selected: null });
  });
});
