import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LeftColumn } from "./LeftColumn";

describe("LeftColumn", () => {
  it("shows the Alarms tab first and switches to Equipment", () => {
    render(<LeftColumn scenario={null} />);
    const equipment = screen.getByRole("tab", { name: "Equipment" });
    expect(screen.getByRole("tab", { name: "Alarms" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("region", { name: "Alarms" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Equipment" })).not.toBeInTheDocument();
    // Radix activates a tab on mouse down (and on focus from the arrow keys)
    fireEvent.mouseDown(equipment, { button: 0, ctrlKey: false });
    expect(equipment).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("region", { name: "Equipment" })).toBeInTheDocument();
  });
  it("is the skip-link target and can take programmatic focus", () => {
    const { container } = render(<LeftColumn scenario={null} />);
    expect(container.querySelector("#alarms-panel")).toHaveAttribute("tabindex", "-1");
  });
});
