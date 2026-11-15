import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataSourceError } from "@/shared/data";

import { ScenarioStatus } from "./ScenarioStatus";

describe("ScenarioStatus", () => {
  it("tells the developer how to start the backend", () => {
    render(
      <ScenarioStatus
        mode="live"
        status="error"
        error={new DataSourceError("unreachable", "down")}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByRole("heading", { name: "Backend not reachable" })).toBeInTheDocument();
    expect(screen.getByText(/uv run uvicorn plumetrace\.api\.main:app/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
  it("renders nothing when ready", () => {
    const { container } = render(
      <ScenarioStatus mode="live" status="ready" error={null} onRetry={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
