import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./webgl", () => ({ hasWebGL2: () => false }));

import { StationView } from "./StationView";

afterEach(() => vi.restoreAllMocks());

describe("StationView without WebGL2", () => {
  it("writes nothing to the console (no error, warning or log)", () => {
    const spies = (["error", "warn", "log", "info"] as const).map((m) => vi.spyOn(console, m));
    render(<StationView />);
    expect(screen.getByRole("img", { name: /Station KS-07/ })).toBeInTheDocument();
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });
  it("shows no 3D controls: no quality menu, no plume legend, no canvas", () => {
    const { container } = render(<StationView />);
    expect(screen.queryByLabelText("3D quality")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset view" })).not.toBeInTheDocument();
    expect(container.querySelector("canvas")).toBeNull();
  });
});
