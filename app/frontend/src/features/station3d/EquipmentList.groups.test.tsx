import { act, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSelectionStore } from "@/shared/selection";

import { EquipmentList } from "./EquipmentList";
import { AREA_ORDER } from "./equipmentLabels";

describe("EquipmentList groups", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));
  afterEach(() => vi.restoreAllMocks());

  it("lists the areas in the fixed order with the planned tags", () => {
    render(<EquipmentList />);
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual([...AREA_ORDER]);
    const tagsOf = (area: string): string[] =>
      within(screen.getByRole("region", { name: area }))
        .getAllByRole("button")
        .map((b) => b.querySelector("span")?.textContent ?? "");
    expect(tagsOf("Inlet")).toEqual(["PIG-101", "V-100"]);
    expect(tagsOf("Compression")).toHaveLength(10);
    expect(tagsOf("Buildings")).toEqual(["CR-901", "MCC-902"]);
    expect(tagsOf("Methane sensors")).toEqual(["AT-101", "AT-102", "AT-103", "AT-104", "AT-105", "AT-106", "AT-107", "AT-108"]);
  });

  it("names each button by tag and type", () => {
    render(<EquipmentList />);
    expect(screen.getByRole("button", { name: "VS-250 Vent stack" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "AT-106 Methane sensor" })).toBeInTheDocument();
  });

  it("scrolls the row of a tag selected elsewhere into view", () => {
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    render(<EquipmentList />);
    scroll.mockClear();
    act(() => useSelectionStore.getState().select("K-202"));
    expect(scroll).toHaveBeenCalledWith({ block: "nearest" });
    expect(screen.getByRole("button", { name: /K-202/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("marks the selected row beyond colour: 4 px bar, semibold tag, primary-text name; unselected rows keep the same bar width", () => {
    render(<EquipmentList />);
    const other = screen.getByRole("button", { name: /K-203/ });
    expect(other).toHaveClass("border-l-4", "border-transparent");
    act(() => useSelectionStore.getState().select("K-202"));
    const row = screen.getByRole("button", { name: /K-202/ });
    expect(row).toHaveClass("border-l-4", "border-accent", "bg-surface-3");
    expect(row.querySelectorAll("span")[0]).toHaveClass("font-semibold");
    expect(row.querySelectorAll("span")[1]).toHaveClass("text-text-1");
    expect(other.querySelectorAll("span")[1]).toHaveClass("text-text-2");
  });

  it("clears the selection when the pressed row is pressed again", () => {
    render(<EquipmentList />);
    const row = screen.getByRole("button", { name: /FL-601/ });
    act(() => row.click());
    act(() => row.click());
    expect(useSelectionStore.getState().selectedTag).toBeNull();
  });
});
