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
  it("describes only what is built: no locating or drafting claim before the agents exist", () => {
    const { container } = render(<MobilePage />);
    expect(
      screen.getByText(
        "PlumeTrace replays simulated leak scenarios from eight fence-line methane sensors at the fictional Station KS-07: methane rises, alarms, wind and a dispersion-model view of the plume.",
      ),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/locates|drafts|work order/i);
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
