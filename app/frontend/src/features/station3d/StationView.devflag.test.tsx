import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./webgl", () => ({ hasWebGL2: () => true }));
vi.mock("./StationCanvas", () => ({ default: () => <div data-testid="canvas" /> }));
vi.mock("./overlays/QualityMenu", () => ({ QualityMenu: () => <div data-testid="menu" /> }));
vi.mock("./plume/PlumeLegend", () => ({ PlumeLegend: () => <div data-testid="legend" /> }));

import { StationView } from "./StationView";

async function show(search: string): Promise<void> {
  window.history.replaceState({}, "", `/${search}`);
  render(<StationView />);
  await act(async () => undefined);
}

afterEach(() => {
  vi.unstubAllEnvs();
  window.history.replaceState({}, "", "/");
});

describe("StationView ?clean flag (dev builds only)", () => {
  it("hides the quality menu and the plume legend, and keeps the canvas, in a dev build", async () => {
    await show("?clean");
    expect(screen.getByTestId("canvas")).toBeInTheDocument();
    expect(screen.queryByTestId("menu")).not.toBeInTheDocument();
    expect(screen.queryByTestId("legend")).not.toBeInTheDocument();
  });
  it("is ignored in a production build", async () => {
    vi.stubEnv("DEV", false);
    await show("?clean");
    expect(screen.getByTestId("menu")).toBeInTheDocument();
    expect(screen.getByTestId("legend")).toBeInTheDocument();
  });
  it("is off without the query", async () => {
    await show("");
    expect(screen.getByTestId("menu")).toBeInTheDocument();
    expect(screen.getByTestId("legend")).toBeInTheDocument();
  });
});
