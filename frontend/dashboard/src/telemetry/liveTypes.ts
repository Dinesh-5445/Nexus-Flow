// Telemetry: Live Wire Event Shape (Day 3)
//
// Represents the ACTUAL shape of events emitted today by Sayan's now-working
// services/api WebSocket stream (`/stream/:execution_id`), confirmed by
// connecting a client to the running service and inspecting the raw JSON
// (see experimental_log.md, Day 3 entry for the reproduction).
//
// CONTRACT MISMATCH (flagged, not silently resolved):
// The schema-accurate `GatewayEvent` in `./types.ts` was modeled on Dinesh's
// Python event producers (src/events/schema.py, src/gateway/router.py,
// src/orchestration/executor.py, src/tools/base.py) and requires a typed
// `payload` for every event_type. `services/api/src/index.ts`'s
// `simulateExecution()` calls `emitEvent(requestId, eventType)` with NO
// payload argument for every lifecycle step, and `emitEvent` only includes a
// `payload` key on the outgoing JSON at all when one is explicitly passed.
// As a result, every event actually observed on `/stream/:execution_id`
// today omits `payload` entirely, e.g.:
//
//   {"event_type":"request_received","request_id":"...","timestamp":...}
//
// This file defines the live wire shape as it actually is (payload optional
// and untyped) instead of forcing it into the stricter GatewayEvent union or
// inventing session_id/tool_name/etc. that was never sent. Worth raising
// with Sayan (services/api's mock event emission carries no payload) and
// Dinesh (the Python reference producers this Node service is meant to
// mirror DO emit payloads, so the two currently diverge).

import { EventLifecycle, type ExecutionStatus } from "./types";

/** The event shape actually sent by services/api's /stream/:execution_id today. */
export interface LiveGatewayEvent {
  event_type: EventLifecycle;
  request_id: string;
  timestamp: number;
  /** Present in the shared schema/GatewayEvent contract; absent in practice today (see note above). */
  payload?: unknown;
}

/** Structural check that a parsed WebSocket message looks like a LiveGatewayEvent. */
export function isLiveGatewayEvent(value: unknown): value is LiveGatewayEvent {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const v = value as Record<string, unknown>;
  return (
    typeof v.event_type === "string" &&
    (Object.values(EventLifecycle) as string[]).includes(v.event_type) &&
    typeof v.request_id === "string" &&
    typeof v.timestamp === "number"
  );
}

// Day 4: Live Execution Status Shape
//
// Mirrors the `InternalExecutionState` Sayan added to services/api/src/types.ts
// today and now returns from `GET /status/:execution_id`, which itself
// mirrors `ExecutionState` from src/state/manager.py (request_id, status,
// start_time, end_time, error). This is the AUTHORITATIVE per-request status
// — see the note in useLiveExecution.ts on why the frontend now fetches this
// instead of re-deriving status from the event stream with statusForEvent()
// (types.ts): that local derivation had drifted from the backend's real
// pending -> running -> completed/failed transitions (e.g. it treated
// REQUEST_RECEIVED as "running", while the backend/state contract keeps a
// request "pending" until EXECUTION_STARTED), which is exactly the kind of
// backend-logic duplication the architecture rules call out to avoid.
export interface LiveExecutionStatus {
  request_id: string;
  status: ExecutionStatus;
  start_time: number;
  end_time?: number;
  error?: string;
}

/** Structural check that a parsed GET /status/:execution_id body looks like a LiveExecutionStatus. */
export function isLiveExecutionStatus(value: unknown): value is LiveExecutionStatus {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const v = value as Record<string, unknown>;
  return (
    typeof v.request_id === "string" &&
    typeof v.status === "string" &&
    typeof v.start_time === "number"
  );
}