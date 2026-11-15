import type { JSX } from "react";

import type { DataSourceError, DataSourceMode, LoadStatus } from "@/shared/data";
import { Button } from "@/shared/ui/button";

/** The command that starts the local backend (from `docs/LOCAL_DEVELOPMENT.md`, run in `app/`). */
const BACKEND_COMMAND = "uv run uvicorn plumetrace.api.main:app --host 127.0.0.1 --port 8000 --reload";

/** Props of {@link ScenarioStatus}. */
export interface ScenarioStatusProps {
  /** Where the data comes from; it decides the unreachable text. */
  mode: DataSourceMode;
  /** Load status of the scenario (or of the scenario list). */
  status: LoadStatus;
  /** The failure behind an `error` status; its `kind` picks the message. */
  error: DataSourceError | null;
  /** Run the failed load again. */
  onRetry: () => void;
}

function RetryButton({ onRetry }: { onRetry: () => void }): JSX.Element {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onRetry}>
      Retry
    </Button>
  );
}

function ErrorBody({ mode, error, onRetry }: Omit<ScenarioStatusProps, "status">): JSX.Element {
  if (error?.kind === "not_found") return <p>Scenario not found.</p>;
  if (error?.kind === "invalid") {
    return <p>Scenario file is invalid. Regenerate it with scripts/export_scenarios.py.</p>;
  }
  if (error?.kind !== "unreachable") {
    return (
      <>
        <p>Scenario could not be loaded.</p>
        <RetryButton onRetry={onRetry} />
      </>
    );
  }
  if (mode === "replay") {
    return (
      <>
        <p>Replay files could not be loaded.</p>
        <RetryButton onRetry={onRetry} />
      </>
    );
  }
  return (
    <>
      <h2 className="text-md font-semibold text-text-1">Backend not reachable</h2>
      <p>Start it from the app folder:</p>
      <code className="block max-w-full overflow-x-auto rounded-sm border border-border-1 bg-surface-1 px-3 py-2 font-mono text-xs text-text-1">
        {BACKEND_COMMAND}
      </code>
      <RetryButton onRetry={onRetry} />
    </>
  );
}

/**
 * Explains why the station view is empty: loading, or the reason a load failed and what to do.
 * It renders nothing once the scenario is ready. A presentational component: the shell passes the
 * store values.
 *
 * @param props - See {@link ScenarioStatusProps}.
 * @returns The status message, or an empty fragment when ready.
 */
export function ScenarioStatus({ mode, status, error, onRetry }: ScenarioStatusProps): JSX.Element {
  if (status === "ready") return <></>;
  return (
    <div role="status" className="flex max-w-xl flex-col items-start gap-2 text-sm text-text-2">
      {status === "error" ? (
        <ErrorBody mode={mode} error={error} onRetry={onRetry} />
      ) : (
        <p>Loading scenario…</p>
      )}
    </div>
  );
}
