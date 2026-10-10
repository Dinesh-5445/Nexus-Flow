import { useState } from "react";
import { EXECUTION_SCENARIOS, type ScenarioId } from "../telemetry/executionScenarios";

interface ExecutionControlsProps {
  busy: boolean;
  /** Why the last start attempt failed (stream or POST /execute). */
  startError: string | null;
  /** Errors from the live stream / status polling for the current execution. */
  connectionError: string | null;
  statusError: string | null;
  onStart: (scenarioId: ScenarioId) => void;
}

export default function ExecutionControls({
  busy,
  startError,
  connectionError,
  statusError,
  onStart,
}: ExecutionControlsProps) {
  const [scenarioId, setScenarioId] = useState<ScenarioId>(EXECUTION_SCENARIOS[0].id);

  return (
    <section className="panel execution-controls" aria-label="Start execution">
      <div className="controls-row">
        <label htmlFor="scenario">Scenario</label>
        <select
          id="scenario"
          value={scenarioId}
          disabled={busy}
          onChange={(e) => setScenarioId(e.target.value as ScenarioId)}
        >
          {EXECUTION_SCENARIOS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => onStart(scenarioId)} disabled={busy}>
          {busy ? "Starting…" : "Start execution"}
        </button>
      </div>
      {startError && <p role="alert" className="notice notice--error">Start failed: {startError}</p>}
      {connectionError && (
        <p role="alert" className="notice notice--error">Stream error: {connectionError}</p>
      )}
      {statusError && (
        <p role="alert" className="notice notice--warning">Status fetch error: {statusError}</p>
      )}
    </section>
  );
}