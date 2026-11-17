import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";
import { useSelectionStore } from "@/shared/selection";

import { EquipmentList } from "./EquipmentList";
import { AREA_OF_TAG } from "./equipmentLabels";

describe("EquipmentList", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));
  it("gives every spec tag an area", () => {
    for (const e of facility.equipment) expect(AREA_OF_TAG[e.tag]).toBeDefined();
  });
  it("selects by click and marks the pressed row", () => {
    render(<EquipmentList />);
    const row = screen.getByRole("button", { name: /VS-250/ });
    fireEvent.click(row);
    expect(useSelectionStore.getState().selectedTag).toBe("VS-250");
    expect(row).toHaveAttribute("aria-pressed", "true");
  });
});
