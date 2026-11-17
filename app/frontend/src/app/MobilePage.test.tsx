import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MobilePage } from "./MobilePage";

describe("MobilePage", () => {
  it("shows the product, the heading, the Simulated label and the desktop hint", () => {
    render(<MobilePage />);
    expect(screen.getByText("PlumeTrace")).toBeInTheDocument();
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Methane leak detection for a simulated compressor station" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/eight fence-line methane sensors at the fictional Station KS-07/)).toBeInTheDocument();
    expect(
      screen.getByText("Open this page in a desktop browser to use the interactive control room."),
    ).toBeInTheDocument();
  });
  it("has no station view and shows the still image with a text alternative", () => {
    render(<MobilePage />);
    expect(screen.queryByLabelText("Station view")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Station KS-07 seen from the south-west/ })).toHaveAttribute(
      "src",
      "/images/station-fallback.jpg",
    );
  });
});
