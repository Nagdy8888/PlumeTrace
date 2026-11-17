import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useScenarioStore } from "@/shared/data";
import { makeReplay } from "@/shared/testing/replayFixture";

import { PlumeLegend } from "./PlumeLegend";

describe("PlumeLegend", () => {
  beforeEach(() => useScenarioStore.setState(useScenarioStore.getInitialState()));

  it("is hidden while no scenario is loaded", () => {
    const { container } = render(<PlumeLegend />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the unit, the five log steps and the honest caption for a loaded scenario", () => {
    useScenarioStore.setState({ scenario: makeReplay(), status: "ready" });
    render(<PlumeLegend />);
    expect(screen.getByText("Methane above background, ppm (model at 1.5 m)")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(["1", "3", "10", "30", "100+"]);
    expect(screen.getByText("Visualisation of the dispersion model. Methane is invisible.")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Methane above background, ppm (model at 1.5 m)" })).toBeInTheDocument();
  });

  it("colours the five steps with the methane ramp tokens, low to high", () => {
    useScenarioStore.setState({ scenario: makeReplay(), status: "ready" });
    const { container } = render(<PlumeLegend />);
    const swatches = Array.from(container.querySelectorAll<HTMLElement>("li > span:first-child"));
    expect(swatches.map((s) => s.style.backgroundColor)).toEqual([
      "var(--ch4-0)",
      "var(--ch4-1)",
      "var(--ch4-2)",
      "var(--ch4-3)",
      "var(--ch4-4)",
    ]);
  });

  it("never states an emission rate or a confidence", () => {
    useScenarioStore.setState({ scenario: makeReplay(), status: "ready" });
    const { container } = render(<PlumeLegend />);
    expect(container.textContent).not.toMatch(/kg\/h|confiden|certain|calibrat/i);
  });
});
