// Dashboard panel prop shapes.
//
// Day 9: these are now populated from the live REST/WebSocket surface
// (POST /execute, GET /status/:id, WS /stream/:id) by telemetry/liveAdapters.ts.
// They are presentation shapes for the panels, not wire contracts — the wire
// shapes live in telemetry/liveTypes.ts and telemetry/types.ts.

import type { ExecutionStatus } from "./telemetry/types";
import type { StreamConnection } from "./telemetry/liveTypes";

/** `idle` = nothing started yet; `starting` = stream opening / request being submitted. */
export type DashboardStatus = "idle" | "starting" | ExecutionStatus;

export interface SessionInfo {
  /** The execution's request_id (what the backend calls the execution ID). */
  executionId: string | null;
  status: DashboardStatus;
  startedAt: string | null;
  endedAt: string | null;
  /** Execution error, if the execution failed. */
  error: string | null;
  stream: StreamConnection;
}

export type EventTone = "info" | "success" | "warning" | "error";

export interface ExecutionEvent {
  id: string;
  type: string;
  timestamp: string;
  /** Milliseconds since the first event observed for this execution. */
  offsetMs: number;
  /** One-line, human-readable description derived from the event payload. */
  summary: string | null;
  tone: EventTone;
  /** True when the event payload carries a Watchdog alert annotation. */
  hasAlert: boolean;
  payload?: unknown;
}

export interface EventCount {
  type: string;
  count: number;
}

export interface Metrics {
  /** API-side request latency: /status end_time - start_time. Null until the execution is terminal. */
  endToEndMs: number | null;
  /** Span between the first and last lifecycle event (Python event timestamps). Null with < 2 events. */
  pipelineMs: number | null;
  eventCount: number;
  eventCounts: EventCount[];
  toolCalls: number;
  /** Sum of `execution_time_ms` reported by tool_execution events. Null when no tool ran. */
  toolTimeMs: number | null;
}

export interface WatchdogAlert {
  id: string;
  executionId: string;
  anomalyType: string;
  toolName: string | null;
  count: number | null;
  /** Timestamp of the event that carried the alert (the alert itself has no timestamp). */
  detectedAt: string;
  message: string;
}