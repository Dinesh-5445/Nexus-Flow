// Telemetry: Execution Event & Status Representation
//
// This file defines how execution events and execution status are represented
// on the frontend. Unlike the loose/placeholder shapes in `../types.ts`, the
// shapes here are modeled directly on the backend contract as it exists today:
//
//   - Event envelope + EventLifecycle : src/events/schema.py        (Dinesh)
//   - request_received / completed / failed payloads : src/gateway/router.py
//   - execution_started payload                       : src/orchestration/executor.py
//   - tool_execution payload (ToolResult.to_event_payload) : src/tools/base.py
//   - execution status values ('pending' | 'running' | 'completed' | 'failed')
//                                                       : src/state/manager.py
//
// SOURCE OF TRUTH: these shapes must track src/events/schema.py and the
// producers above. If those change, this file is the place to update.
//
// TRANSPORT NOTE: no real transport exists yet. Sayan's REST/WebSocket layer
// (services/api/src/index.ts) is currently stubbed (/execute and /stream/:id
// have no implementation). This file only defines the *representation*; see
// mockEvents.ts / MockEventSource.ts for the temporary mocked feed used until
// a real WebSocket/REST source is available.

/**
 * Mirrors src/events/schema.py::EventLifecycle.
 * This is the outer `event_type` carried on every Event envelope.
 */
export enum EventLifecycle {
  REQUEST_RECEIVED = "request_received",
  EXECUTION_STARTED = "execution_started",
  TOOL_EXECUTION = "tool_execution",
  COMPLETED = "completed",
  FAILED = "failed",
}

/** Payload for EventLifecycle.REQUEST_RECEIVED (see gateway/router.py). */
export interface RequestReceivedPayload {
  session_id: string;
  messages_count: number;
}

/** Payload for EventLifecycle.EXECUTION_STARTED (see orchestration/executor.py). */
export interface ExecutionStartedPayload {
  provider_model: string;
}

/**
 * Payload for EventLifecycle.TOOL_EXECUTION.
 * Produced by ToolResult.to_event_payload() in src/tools/base.py, and is
 * also the exact shape Koushik's Watchdog consumes.
 *
 * KNOWN CONTRACT QUIRK (not resolved here, flagged as-is):
 * to_event_payload() nests its own `request_id`, `timestamp`, and a literal
 * `event_type: "tool_called"` inside the payload, which duplicates/conflicts
 * with the outer envelope's `request_id`/`timestamp`/`event_type` (the outer
 * event_type is EventLifecycle.TOOL_EXECUTION, not "tool_called"). Both
 * fields are kept below so the frontend representation matches the real
 * payload byte-for-byte. This should be raised with Dinesh/Koushik; the
 * frontend does not silently pick one interpretation over the other.
 */
export interface ToolExecutionPayload {
  request_id: string;
  /** Literal string emitted by the backend today; see quirk note above. */
  event_type: "tool_called";
  timestamp: number;
  tool_name: string;
  status: "completed" | "failed";
  session_id: string;
  tool_call_id: string;
  execution_time_ms: number;
  error: string | null;
}

/** Payload for EventLifecycle.COMPLETED (see gateway/router.py). */
export interface CompletedPayload {
  status: "success";
}

/** Payload for EventLifecycle.FAILED (see gateway/router.py). */
export interface FailedPayload {
  error: string;
}

/**
 * Discriminated union mirroring Event.to_dict() from src/events/schema.py,
 * with `payload` narrowed per event_type instead of the backend's untyped
 * Dict[str, Any]. `event_type` is the discriminant.
 */
export type GatewayEvent =
  | { event_type: EventLifecycle.REQUEST_RECEIVED; request_id: string; timestamp: number; payload: RequestReceivedPayload }
  | { event_type: EventLifecycle.EXECUTION_STARTED; request_id: string; timestamp: number; payload: ExecutionStartedPayload }
  | { event_type: EventLifecycle.TOOL_EXECUTION; request_id: string; timestamp: number; payload: ToolExecutionPayload }
  | { event_type: EventLifecycle.COMPLETED; request_id: string; timestamp: number; payload: CompletedPayload }
  | { event_type: EventLifecycle.FAILED; request_id: string; timestamp: number; payload: FailedPayload };

/**
 * Mirrors ExecutionState.status from src/state/manager.py.
 * This is the derived, per-request execution status the frontend tracks —
 * distinct from any single event, it's the running interpretation of the
 * event sequence seen so far for a request_id.
 */
export type ExecutionStatus = "pending" | "running" | "completed" | "failed";

/** Per-request execution status derived from the observed event stream. */
export interface ExecutionStatusInfo {
  requestId: string;
  status: ExecutionStatus;
  startedAt: number | null;
  endedAt: number | null;
  error: string | null;
}

/**
 * Derives an ExecutionStatus from a GatewayEvent, mirroring the transitions
 * StateManager performs server-side (create_state -> 'pending',
 * REQUEST_RECEIVED/EXECUTION_STARTED/TOOL_EXECUTION -> 'running',
 * COMPLETED -> 'completed', FAILED -> 'failed').
 */
export function statusForEvent(eventType: EventLifecycle): ExecutionStatus {
  switch (eventType) {
    case EventLifecycle.COMPLETED:
      return "completed";
    case EventLifecycle.FAILED:
      return "failed";
    case EventLifecycle.REQUEST_RECEIVED:
    case EventLifecycle.EXECUTION_STARTED:
    case EventLifecycle.TOOL_EXECUTION:
      return "running";
    default:
      return "pending";
  }
}