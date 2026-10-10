// Telemetry: Live Wire Event Shape (Day 3)
//
// Represents the ACTUAL shape of events emitted by Sayan's services/api
// WebSocket stream (`/stream/:execution_id`), confirmed by connecting a
// client to the running service and inspecting the raw JSON.
//
// Day 9 update: the earlier mismatch (services/api's mocked execution sent no
// `payload`) is resolved. Python's EventStream is now the single source of
// lifecycle events (src/main.py stdout writer -> services/api onEvent ->
// emitEvent), and every event on `/stream/:execution_id` carries its Python
// `payload`, e.g.:
//
//   {"event_type":"request_received","request_id":"...","timestamp":...,
//    "payload":{"session_id":"...","messages_count":1}}
//
// `payload` is still typed `unknown` here (per-event shapes are documented in
// ./types.ts and narrowed by ./livePayloads.ts) rather than forcing the live
// wire shape into the stricter GatewayEvent union.

import { EventLifecycle, type ExecutionStatus } from "./types";

/** State of the dashboard's WebSocket connection to /stream/:execution_id. */
export type StreamConnection = "idle" | "connecting" | "open" | "closed" | "error";

/** The event shape actually sent by services/api's /stream/:execution_id today. */
export interface LiveGatewayEvent {
  event_type: EventLifecycle;
  request_id: string;
  timestamp: number;
  /**
   * Day 9: now present on every event relayed from Python (src/main.py's
   * stdout writer -> services/api onEvent -> emitEvent). Kept `unknown`; use
   * the readers in livePayloads.ts rather than casting.
   */
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