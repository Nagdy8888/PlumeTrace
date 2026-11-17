import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("./webgl", () => ({ hasWebGL2: () => false }));

import { StationView } from "./StationView";

describe("StationView", () => {
  it("shows the static fallback without WebGL2", () => {
    render(<StationView />);
    expect(screen.getByRole("img", { name: /Station KS-07 seen from the south-west/ })).toBeInTheDocument();
    expect(screen.getByText(/3D view unavailable on this device/)).toBeInTheDocument();
  });
});
