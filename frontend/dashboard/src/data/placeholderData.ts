// LOCAL PLACEHOLDER DATA ONLY.
// This is NOT the final REST/WebSocket contract.
// Do not treat these values as agreed/final.

import type { SessionInfo, ExecutionEvent, Metrics, WatchdogAlert } from "../types";

export const placeholderSession: SessionInfo = {
  sessionId: "local-placeholder",
  status: "unknown",
  startedAt: null,
};

export const placeholderEvents: ExecutionEvent[] = [];

export const placeholderMetrics: Metrics = {
  latencyMs: null,
  throughputPerSec: null,
};

export const placeholderAlerts: WatchdogAlert[] = [];