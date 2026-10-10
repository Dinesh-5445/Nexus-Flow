// Telemetry: Execution Event & Status Representation
//
// This file defines how execution events and execution status are represented
// on the frontend. Unlike the loose/placeholder shapes in `../types.ts`, the
// shapes here are modeled directly on the backend contract as it exists today:
//
//   - Event envelope + EventLifecycle : src/events/schema.py        (Dinesh)
//   - request_received / completed / failed payloads : src/gateway/router.py
//   - execution_started / llm_execution payloads      : src/orchestration/executor.py
//   - tool_execution payload (ToolResult.to_event_payload) : src/tools/base.py
//   - execution status values ('pending' | 'running' | 'completed' | 'failed')
//                                                       : src/state/manager.py
//
// SOURCE OF TRUTH: these shapes must track src/events/schema.py and the
// producers above. If those change, this file is the place to update.
//
// Day 8 fix: EventLifecycle here was missing LLM_EXECUTION, which
// src/events/schema.py and src/orchestration/executor.py added back on Day 5
// (lifecycle is REQUEST_RECEIVED -> EXECUTION_STARTED -> LLM_EXECUTION ->
// TOOL_EXECUTION* -> COMPLETED/FAILED, per logs/log.md Day 5). Added below so
// the frontend event union matches the real lifecycle.
//
// TRANSPORT NOTE: Sayan's REST/WebSocket layer (services/api/src/index.ts)
// is implemented today (POST /execute, GET /status/:id, WS /stream/:id) —
// see WebSocketEventSource.ts / useLiveExecution.ts. This file only defines
// the *representation*; see mockEvents.ts / MockEventSource.ts for the
// still-useful mocked feed used for UI development without a backend.

/**
 * Mirrors src/events/schema.py::EventLifecycle.
 * This is the outer `event_type` carried on every Event envelope.
 */
export enum EventLifecycle {
  REQUEST_RECEIVED = "request_received",
  EXECUTION_STARTED = "execution_started",
  LLM_EXECUTION = "llm_execution",
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
 * Payload for EventLifecycle.LLM_EXECUTION, published right after the
 * provider responds (see orchestration/executor.py: `{"model": ...,
 * "usage": response.usage}`). `usage` is left untyped since
 * src/providers/base.py does not pin down a concrete shape for it.
 */
export interface LlmExecutionPayload {
  model: string;
  usage: unknown;
}

/**
 * Payload for EventLifecycle.TOOL_EXECUTION.
 * Produced by ToolResult.to_event_payload() in src/tools/base.py, and is
 * also the exact shape Koushik's Watchdog consumes.
 *
 * Day 9 note: to_event_payload() still nests its own `request_id`, `timestamp`
 * and `event_type` inside the payload, duplicating the outer envelope's
 * fields. The nested `event_type` used to be the literal "tool_called"; the
 * current src/tools/base.py emits EventLifecycle.TOOL_EXECUTION.value
 * ("tool_execution"), which is also what the live wire shows, so it is typed
 * that way here. The duplication itself is kept as-is to match the payload
 * byte-for-byte.
 */
export interface ToolExecutionPayload {
  request_id: string;
  /** Mirrors the outer envelope's event_type; see Day 9 note above. */
  event_type: "tool_execution";
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
  | { event_type: EventLifecycle.LLM_EXECUTION; request_id: string; timestamp: number; payload: LlmExecutionPayload }
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
    case EventLifecycle.LLM_EXECUTION:
    case EventLifecycle.TOOL_EXECUTION:
      return "running";
    default:
      return "pending";
  }
}