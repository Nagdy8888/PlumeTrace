import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("shows its meaning as text next to a decorative marker", () => {
    const { container } = render(<StatusBadge tone="high">High priority</StatusBadge>);
    expect(screen.getByText("High priority")).toBeInTheDocument();
    const marker = container.querySelector("[aria-hidden='true']");
    expect(marker).toHaveClass("bg-alarm-high");
  });
});
