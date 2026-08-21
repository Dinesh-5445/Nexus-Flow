import { useState } from "react";
import { useLiveExecution } from "../telemetry/useLiveExecution";

// Day 3: minimal execution-status/event view, wired to Sayan's now-working
// REST/WebSocket stream (POST /execute, then WS /stream/:execution_id).
// Deliberately minimal/unstyled and separate from DashboardLayout's existing
// placeholder-fed panels per today's scope — no visual polish, no full
// dashboard integration yet.
//
// Shows: execution ID, derived status, ordered lifecycle events, and basic
// timing (elapsed time since the first observed event). Event payloads are
// NOT rendered — the live stream doesn't send any today (see
// telemetry/liveTypes.ts for the contract-mismatch note), so there is
// nothing real to show without inventing it.

function formatElapsed(fromSeconds: number, toSeconds: number): string {
  return `+${Math.round((toSeconds - fromSeconds) * 1000)} ms`;
}

export default function ExecutionMonitor() {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const live = useLiveExecution(requestId);

  async function handleStart() {
    setStarting(true);
    setStartError(null);
    const newRequestId = `req-${Date.now()}`;

    try {
      // Relative URL so this goes through the Vite dev proxy (vite.config.ts)
      // to services/api, avoiding services/api's missing CORS headers.
      const res = await fetch("/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: newRequestId,
          messages: [{ role: "user", content: "Day 3 telemetry test" }],
          session_id: "dashboard-manual-trigger",
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body?.error === "string" ? body.error : `Request failed with status ${res.status}`
        );
      }

      setRequestId(newRequestId);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }

  return (
    <section className="panel execution-monitor">
      <h2>Execution Monitor (live)</h2>
      <p>
        Consumes Sayan&apos;s REST/WebSocket stream directly — not fed by
        placeholderData.ts.
      </p>

      <button onClick={handleStart} disabled={starting}>
        {starting ? "Starting…" : "Start test execution"}
      </button>
      {startError && <p role="alert">Start failed: {startError}</p>}

      {requestId && (
        <div>
          <p>Execution ID: {live.requestId}</p>
          <p>Status: {live.status}</p>
          {live.connectionError && <p role="alert">Stream error: {live.connectionError}</p>}

          <h3>Lifecycle events</h3>
          {live.events.length === 0 ? (
            <p>Waiting for events…</p>
          ) : (
            <ul>
              {live.events.map((event, i) => (
                <li key={`${event.event_type}-${i}`}>
                  {event.event_type}
                  {live.startedAt !== null && ` — ${formatElapsed(live.startedAt, event.timestamp)}`}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}