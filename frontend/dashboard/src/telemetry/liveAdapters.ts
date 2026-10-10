// Telemetry: Live -> Dashboard Adapter (Day 8, extended Day 9)
//
// Bridges the live execution state from useLiveExecution.ts (Sayan's
// REST/WebSocket surface: POST /execute, GET /status/:id, WS /stream/:id) to
// the panel prop shapes in ../types.ts. Presentation-only: execution status
// itself is never re-derived here — it comes from GET /status per
// useLiveExecution's contract. Event summaries, offsets and metrics are
// arithmetic/formatting over data the backend already sent.
//
// Watchdog alerts (Day 9): read from `payload.watchdog_alert` on
// tool_execution events — see livePayloads.ts for how they reach the browser.

import type { LiveExecutionState } from "./useLiveExecution";
import type { LiveGatewayEvent } from "./liveTypes";
import type { RunPhase } from "./useExecutionRun";
import {
  readCompletedStatus,
  readExecutionStarted,
  readFailedError,
  readLlmPayload,
  readRequestReceived,
  readToolPayload,
  readWatchdogAlert,
} from "./livePayloads";
import type {
  SessionInfo,
  ExecutionEvent,
  EventTone,
  Metrics,
  WatchdogAlert,
  DashboardStatus,
} from "../types";

function toIso(seconds: number | null): string | null {
  return seconds === null ? null : new Date(seconds * 1000).toISOString();
}

function humanize(snake: string): string {
  return snake.replace(/_/g, " ");
}

/** Maps the authoritative live execution status to a SessionInfo for SessionPanel. */
export function toSessionInfo(live: LiveExecutionState, phase: RunPhase): SessionInfo {
  let status: DashboardStatus;
  if (!live.requestId) {
    status = "idle";
  } else if (phase === "connecting" || phase === "submitting") {
    status = "starting";
  } else {
    status = live.status;
  }

  return {
    executionId: live.requestId || null,
    status,
    startedAt: toIso(live.startedAt),
    endedAt: toIso(live.endedAt),
    error: live.error,
    stream: live.connection,
  };
}

function summarize(event: LiveGatewayEvent): string | null {
  switch (event.event_type) {
    case "request_received": {
      const p = readRequestReceived(event.payload);
      if (!p) return null;
      const parts: string[] = [];
      if (p.sessionId) parts.push(`session ${p.sessionId}`);
      if (p.messagesCount !== null) {
        parts.push(`${p.messagesCount} message${p.messagesCount === 1 ? "" : "s"}`);
      }
      return parts.length ? parts.join(" · ") : null;
    }
    case "execution_started": {
      const p = readExecutionStarted(event.payload);
      return p?.model ? `model ${p.model}` : null;
    }
    case "llm_execution": {
      const p = readLlmPayload(event.payload);
      if (!p) return null;
      const parts: string[] = [];
      if (p.model) parts.push(p.model);
      if (p.totalTokens !== null) parts.push(`${p.totalTokens} tokens`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "tool_execution": {
      const p = readToolPayload(event.payload);
      if (!p) return null;
      const parts: string[] = [p.toolName];
      if (p.status) parts.push(p.status);
      if (p.executionTimeMs !== null) parts.push(`${p.executionTimeMs} ms`);
      if (p.error) parts.push(p.error);
      return parts.join(" · ");
    }
    case "completed": {
      const status = readCompletedStatus(event.payload);
      return status ? `status ${status}` : null;
    }
    case "failed":
      return readFailedError(event.payload);
    default:
      return null;
  }
}

function toneFor(event: LiveGatewayEvent, hasAlert: boolean): EventTone {
  if (event.event_type === "failed") return "error";
  if (event.event_type === "tool_execution") {
    const tool = readToolPayload(event.payload);
    if (tool?.status === "failed") return "error";
  }
  if (hasAlert) return "warning";
  if (event.event_type === "completed") return "success";
  return "info";
}

/** Maps the observed lifecycle events to the ExecutionEvent[] EventStreamPanel expects. */
export function toExecutionEvents(live: LiveExecutionState): ExecutionEvent[] {
  const origin = live.firstEventAt;
  return live.events.map((event, index) => {
    const hasAlert = readWatchdogAlert(event.payload) !== null;
    return {
      id: `${live.requestId}-${index}-${event.event_type}`,
      type: event.event_type,
      timestamp: toIso(event.timestamp) ?? "",
      offsetMs: origin === null ? 0 : Math.round((event.timestamp - origin) * 1000),
      summary: summarize(event),
      tone: toneFor(event, hasAlert),
      hasAlert,
      payload: event.payload,
    };
  });
}

const LIFECYCLE_ORDER = [
  "request_received",
  "execution_started",
  "llm_execution",
  "tool_execution",
  "completed",
  "failed",
] as const;

/**
 * Basic telemetry derived from data the backend already sent:
 *  - endToEndMs: /status end_time - start_time (API-side clock; includes
 *    gateway process startup). Null until the execution is terminal.
 *  - pipelineMs: span between first and last lifecycle event (Python clock).
 *  - event activity: counts per lifecycle type.
 *  - tool activity: number of tool_execution events and the sum of their
 *    reported execution_time_ms.
 */
export function toMetrics(live: LiveExecutionState): Metrics {
  const endToEndMs =
    live.startedAt !== null && live.endedAt !== null
      ? Math.round((live.endedAt - live.startedAt) * 1000)
      : null;

  const pipelineMs =
    live.events.length >= 2 && live.firstEventAt !== null && live.lastEventAt !== null
      ? Math.round((live.lastEventAt - live.firstEventAt) * 1000)
      : null;

  const counts = new Map<string, number>();
  let toolCalls = 0;
  let toolTime = 0;
  let sawToolTime = false;
  for (const event of live.events) {
    counts.set(event.event_type, (counts.get(event.event_type) ?? 0) + 1);
    if (event.event_type === "tool_execution") {
      toolCalls += 1;
      const tool = readToolPayload(event.payload);
      if (tool?.executionTimeMs != null) {
        toolTime += tool.executionTimeMs;
        sawToolTime = true;
      }
    }
  }

  return {
    endToEndMs,
    pipelineMs,
    eventCount: live.events.length,
    eventCounts: LIFECYCLE_ORDER.filter((t) => counts.has(t)).map((t) => ({
      type: t,
      count: counts.get(t) ?? 0,
    })),
    toolCalls,
    toolTimeMs: sawToolTime ? Math.round(toolTime * 100) / 100 : null,
  };
}

/** Extracts Watchdog alerts carried on tool_execution event payloads. */
export function toWatchdogAlerts(live: LiveExecutionState): WatchdogAlert[] {
  const alerts: WatchdogAlert[] = [];
  live.events.forEach((event, index) => {
    const alert = readWatchdogAlert(event.payload);
    if (!alert) return;

    let message = humanize(alert.anomalyType);
    if (alert.toolName) message += ` — ${alert.toolName}`;
    if (alert.count !== null) message += ` (count ${alert.count})`;

    alerts.push({
      id: `${live.requestId}-${index}-${alert.anomalyType}`,
      executionId: live.requestId,
      anomalyType: alert.anomalyType,
      toolName: alert.toolName,
      count: alert.count,
      detectedAt: toIso(event.timestamp) ?? "",
      message,
    });
  });
  return alerts;
}