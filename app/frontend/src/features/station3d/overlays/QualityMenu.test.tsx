import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RESET_VIEW_EVENT, useStationStore } from "../store";
import { QualityMenu } from "./QualityMenu";

describe("QualityMenu", () => {
  beforeEach(() => {
    localStorage.clear();
    useStationStore.setState(useStationStore.getInitialState());
  });

  it("offers Auto, High, Medium and Low and shows the automatic tier", () => {
    render(<QualityMenu />);
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Auto (High)", "High", "Medium", "Low"]);
  });

  it("shows the tier the monitor chose after a decline", () => {
    useStationStore.getState().decline();
    render(<QualityMenu />);
    expect(screen.getByRole("option", { name: "Auto (Medium)" })).toBeInTheDocument();
  });

  it("writes the choice to the store", () => {
    render(<QualityMenu />);
    fireEvent.change(screen.getByLabelText("3D quality"), { target: { value: "low" } });
    expect(useStationStore.getState().override).toBe("low");
    expect(localStorage.getItem("plumetrace.quality")).toBe("low");
  });

  it("shows a visible Quality caption and the R shortcut next to Reset view", () => {
    render(<QualityMenu />);
    expect(screen.getByText("Quality")).toBeVisible();
    const button = screen.getByRole("button", { name: "Reset view" });
    expect(button).toHaveAttribute("aria-keyshortcuts", "R");
    expect(within(button).getByText("R")).toBeVisible();
  });

  it("Reset view dispatches the reset event", () => {
    const heard = vi.fn();
    window.addEventListener(RESET_VIEW_EVENT, heard);
    render(<QualityMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Reset view" }));
    window.removeEventListener(RESET_VIEW_EVENT, heard);
    expect(heard).toHaveBeenCalledTimes(1);
  });
});
