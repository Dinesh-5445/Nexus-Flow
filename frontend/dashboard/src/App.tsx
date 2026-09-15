import { useState } from "react";
import DashboardLayout from "./DashboardLayout";
import { useLiveExecution } from "./telemetry/useLiveExecution";
import { toSessionInfo, toExecutionEvents, toMetrics } from "./telemetry/liveAdapters";
import { placeholderAlerts } from "./data/placeholderData";

// Day 8: Final V1 integration. DashboardLayout now renders live data from
// Sayan's finalized REST/WebSocket surface (POST /execute, GET /status/:id,
// WS /stream/:id) via useLiveExecution + liveAdapters.ts, replacing both
// data/placeholderData.ts and the separate unstyled ExecutionMonitor panel
// from Day 3 (folded into the controls below — rendering both was a
// duplicate view of the same execution).
//
// AlertsPanel still receives placeholderAlerts ([]) — there is no
// REST/WebSocket endpoint exposing Watchdog alerts yet. See today's report
// (Coordination required) for what that needs from Dinesh/Koushik/Sayan.
//
// Known limitation, not fixed here (outside today's scope): src/main.py
// does not yet stream intermediate lifecycle Event lines to stdout (only
// the final GatewayResponse), so services/api's onEvent callback never
// fires beyond the request_received bookkeeping event, and GET /status
// never advances past "pending". Confirmed by running services/api and
// src/main.py directly (see today's report). This blocks full real-time
// validation and requires coordination with Dinesh.
export default function App() {
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
          messages: [{ role: "user", content: "Dashboard live execution" }],
          session_id: "dashboard-live",
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
    <>
      <section className="panel execution-controls">
        <button onClick={handleStart} disabled={starting}>
          {starting ? "Starting…" : "Start execution"}
        </button>
        {startError && <p role="alert">Start failed: {startError}</p>}
        {live.connectionError && <p role="alert">Stream error: {live.connectionError}</p>}
        {live.statusError && <p role="alert">Status fetch error: {live.statusError}</p>}
      </section>
      <DashboardLayout
        session={toSessionInfo(live)}
        events={toExecutionEvents(live)}
        metrics={toMetrics(live)}
        alerts={placeholderAlerts}
      />
    </>
  );
}