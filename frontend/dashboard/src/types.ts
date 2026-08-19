// Types for dashboard data shapes.
// Marked as PLACEHOLDER until the real contracts exist:
//   - Session/status shape: Sayan's REST/WebSocket API
//   - Event shape: Dinesh's shared event schema
//   - Alert shape: Koushik's watchdog alert format
// Fields are kept loose (optional / unknown) on purpose —
// do not treat this as an agreed final contract.

export interface SessionInfo {
  sessionId: string;
  status: string; // real enum values TBD by Dinesh's event schema
  startedAt: string | null;
}

export interface ExecutionEvent {
  id: string;
  type: string;
  timestamp: string;
  payload?: unknown; // shape TBD by Dinesh's event schema
}

export interface Metrics {
  latencyMs: number | null;
  throughputPerSec: number | null;
}

export interface WatchdogAlert {
  id: string;
  message: string; // shape TBD by Koushik's alert format
}