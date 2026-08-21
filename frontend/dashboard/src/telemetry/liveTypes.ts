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

import { EventLifecycle } from "./types";

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