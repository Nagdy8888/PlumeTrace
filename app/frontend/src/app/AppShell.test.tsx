import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("shows the product name and the simulated-data label", () => {
    render(<AppShell />);
    expect(screen.getByRole("heading", { level: 1, name: "PlumeTrace" })).toBeInTheDocument();
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Station view" })).toBeInTheDocument();
  });
});
