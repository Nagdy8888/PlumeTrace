import { beforeEach, describe, expect, it } from "vitest";

import { useSelectionStore } from ".";

describe("selectionStore", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));

  it("selects a tag, and selecting it again clears it", () => {
    useSelectionStore.getState().select("K-202");
    expect(useSelectionStore.getState().selectedTag).toBe("K-202");
    useSelectionStore.getState().select("K-202");
    expect(useSelectionStore.getState().selectedTag).toBeNull();
  });
  it("selecting another tag replaces the selection; null clears it", () => {
    useSelectionStore.getState().select("K-202");
    useSelectionStore.getState().select("VS-250");
    expect(useSelectionStore.getState().selectedTag).toBe("VS-250");
    useSelectionStore.getState().select(null);
    expect(useSelectionStore.getState().selectedTag).toBeNull();
  });
  it("hover is independent of selection", () => {
    useSelectionStore.getState().select("K-202");
    useSelectionStore.getState().hover("VS-250");
    expect(useSelectionStore.getState()).toMatchObject({ selectedTag: "K-202", hoveredTag: "VS-250" });
    useSelectionStore.getState().hover(null);
    expect(useSelectionStore.getState().hoveredTag).toBeNull();
  });
});
