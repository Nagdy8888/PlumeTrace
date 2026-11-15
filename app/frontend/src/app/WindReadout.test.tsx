import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WindReadout } from "./WindReadout";

describe("WindReadout", () => {
  it("formats speed, compass point, degrees and stability", () => {
    render(<WindReadout conditions={{ windSpeed_m_s: 3.46, windFrom_deg: 250.4, stability: "D" }} />);
    expect(screen.getByText("Wind 3.5 m/s from WSW (250°) · Stability D")).toBeInTheDocument();
  });
  it("shows a dash without data", () => {
    render(<WindReadout conditions={null} />);
    expect(screen.getByText("Wind —")).toBeInTheDocument();
  });
});
