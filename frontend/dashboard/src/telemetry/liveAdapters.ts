// Telemetry: Live -> Dashboard Adapter (Day 8)
//
// Bridges the real live execution state from useLiveExecution.ts (backed by
// Sayan's finalized REST/WebSocket surface: POST /execute, GET /status/:id,
// WS /stream/:id) to the panel prop shapes in ../types.ts (SessionInfo,
// ExecutionEvent, Metrics) that DashboardLayout/SessionPanel/
// EventStreamPanel/MetricsPanel already render. This is a small, focused
// adapter layer so DashboardLayout can show real data instead of
// data/placeholderData.ts, without rewriting those panel components today.
//
// Scope note: WatchdogAlert is intentionally NOT adapted here. There is
// currently no REST/WebSocket endpoint exposing Watchdog alerts —
// src/watchdog/detector.py is only wired in-process via src/main.py and its
// `alerts` list is never serialized across the API boundary. AlertsPanel
// keeps receiving an empty list (data/placeholderData.ts's
// placeholderAlerts) until that interface exists; see today's report for
// the coordination this requires with Dinesh (main.py/event wiring),
// Koushik (Watchdog, alert shape), and Sayan (exposing it via REST/WS).

import type { LiveExecutionState } from "./useLiveExecution";
import type { SessionInfo, ExecutionEvent, Metrics } from "../types";

function toIso(seconds: number | null): string | null {
  return seconds === null ? null : new Date(seconds * 1000).toISOString();
}

/** Maps the authoritative live execution status to a SessionInfo for SessionPanel. */
export function toSessionInfo(live: LiveExecutionState): SessionInfo {
  return {
    sessionId: live.requestId || "—",
    status: live.status,
    startedAt: toIso(live.startedAt),
  };
}

/** Maps the observed lifecycle events to the ExecutionEvent[] EventStreamPanel expects. */
export function toExecutionEvents(live: LiveExecutionState): ExecutionEvent[] {
  return live.events.map((event, index) => ({
    id: `${live.requestId}-${index}-${event.event_type}`,
    type: event.event_type,
    timestamp: toIso(event.timestamp) ?? "",
    payload: event.payload,
  }));
}

/**
 * Derives presentation-only metrics from timestamps already delivered by the
 * backend (elapsed time between the first observed event and the terminal
 * status). This does not re-derive execution status itself — that still
 * comes from GET /status per useLiveExecution's existing contract — it only
 * does arithmetic over timestamps already sent.
 *
 * throughputPerSec is left null: no aggregate telemetry endpoint exists yet
 * (the live view tracks one execution at a time), so it isn't invented.
 */
export function toMetrics(live: LiveExecutionState): Metrics {
  const latencyMs =
    live.startedAt !== null && live.endedAt !== null
      ? Math.round((live.endedAt - live.startedAt) * 1000)
      : null;

  return {
    latencyMs,
    throughputPerSec: null,
  };
}