import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";

describe("AppShell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("x")));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });
  it("shows the product name, the simulated label and the panel regions", () => {
    render(<AppShell />);
    expect(screen.getByRole("heading", { level: 1, name: "PlumeTrace" })).toBeInTheDocument();
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Alarms" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Station log" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Trends" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Station view" })).toBeInTheDocument();
  });
});
