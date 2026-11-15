import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataSourceError, type DataSourceErrorKind } from "@/shared/data";

import { ScenarioStatus } from "./ScenarioStatus";

const show = (
  mode: "live" | "replay",
  kind: DataSourceErrorKind | null,
  onRetry: () => void = () => undefined,
) =>
  render(
    <ScenarioStatus
      mode={mode}
      status="error"
      error={kind === null ? null : new DataSourceError(kind, "detail")}
      onRetry={onRetry}
    />,
  );

describe("ScenarioStatus by error kind", () => {
  it("shows the loading text", () => {
    render(<ScenarioStatus mode="live" status="loading" error={null} onRetry={() => undefined} />);
    expect(screen.getByText("Loading scenario…")).toBeInTheDocument();
  });

  it("not_found: its own message, never the backend text", () => {
    show("live", "not_found");
    expect(screen.getByText("Scenario not found.")).toBeInTheDocument();
    expect(screen.queryByText("Backend not reachable")).not.toBeInTheDocument();
  });

  it("invalid: names the export script, never the backend text", () => {
    show("live", "invalid");
    expect(
      screen.getByText("Scenario file is invalid. Regenerate it with scripts/export_scenarios.py."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Backend not reachable")).not.toBeInTheDocument();
  });

  it("an error without a kind does not claim the backend is down", () => {
    show("live", null);
    expect(screen.getByText("Scenario could not be loaded.")).toBeInTheDocument();
    expect(screen.queryByText("Backend not reachable")).not.toBeInTheDocument();
  });

  it("replay + unreachable: the replay-files text, no backend command", () => {
    show("replay", "unreachable");
    expect(screen.getByText("Replay files could not be loaded.")).toBeInTheDocument();
    expect(screen.queryByText(/uvicorn/)).not.toBeInTheDocument();
  });

  it("Retry calls onRetry", () => {
    const onRetry = vi.fn();
    show("live", "unreachable", onRetry);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
