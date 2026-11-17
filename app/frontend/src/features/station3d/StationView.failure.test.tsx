import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const canvas = vi.hoisted(() => ({
  handlers: { lost: () => undefined, restored: () => undefined } as { lost: () => void; restored: () => void },
  fail: false,
}));

vi.mock("./webgl", () => ({ hasWebGL2: () => true }));
vi.mock("./StationCanvas", () => ({
  default: (props: { onContextLost: () => void; onContextRestored: () => void }) => {
    if (canvas.fail) throw new Error("model failed to load");
    canvas.handlers.lost = props.onContextLost;
    canvas.handlers.restored = props.onContextRestored;
    return <div data-testid="canvas" />;
  },
}));
vi.mock("./overlays/QualityMenu", () => ({ QualityMenu: () => <div data-testid="menu" /> }));
vi.mock("./plume/PlumeLegend", () => ({ PlumeLegend: () => <div data-testid="legend" /> }));

import { StationView } from "./StationView";

const FALLBACK = /3D view unavailable on this device/;

describe("StationView failures", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    canvas.fail = false;
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows the canvas, menu and legend when WebGL 2 works", async () => {
    render(<StationView />);
    await act(async () => undefined);
    expect(screen.getByTestId("canvas")).toBeInTheDocument();
    expect(screen.getByTestId("menu")).toBeInTheDocument();
    expect(screen.queryByText(FALLBACK)).not.toBeInTheDocument();
  });

  it("falls back, logging once, when the canvas or the model throws", async () => {
    canvas.fail = true;
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(<StationView />);
    await act(async () => undefined);
    expect(screen.getByText(FALLBACK)).toBeInTheDocument();
    expect(screen.queryByTestId("menu")).not.toBeInTheDocument();
    const ours = error.mock.calls.filter((c) => c[0] === "station view failed");
    expect(ours).toHaveLength(1);
  });

  it("falls back when the context stays lost for 3 s", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(<StationView />);
    await act(async () => undefined);
    act(() => canvas.handlers.lost());
    act(() => void vi.advanceTimersByTime(2999));
    expect(screen.queryByText(FALLBACK)).not.toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(1));
    expect(screen.getByText(FALLBACK)).toBeInTheDocument();
    expect(error).toHaveBeenCalledTimes(1);
  });

  it("keeps the canvas when the context is restored within 3 s", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(<StationView />);
    await act(async () => undefined);
    act(() => canvas.handlers.lost());
    act(() => void vi.advanceTimersByTime(2000));
    act(() => canvas.handlers.restored());
    act(() => void vi.advanceTimersByTime(5000));
    expect(screen.getByTestId("canvas")).toBeInTheDocument();
    expect(error).not.toHaveBeenCalled();
  });
});
