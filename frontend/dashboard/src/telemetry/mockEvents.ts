// Telemetry: Mocked Events
//
// MOCK DATA ONLY. Do not depend on the real execution pipeline — Sayan's
// REST/WebSocket layer (services/api) has no working /execute or
// /stream/:execution_id yet, and there is no live event feed to connect to.
//
// These generators build a plausible sequence of GatewayEvents for a single
// request, shaped exactly like the payloads the backend actually produces
// today (see types.ts header for the source files). They exist so the
// event-consumption foundation (EventSource.ts / useTelemetryEvents.ts) has
// something real to consume and can be exercised/tested before any real
// transport exists.

import {
  EventLifecycle,
  type GatewayEvent,
} from "./types";

let mockCounter = 0;

/** Generates a simple unique-enough id for mock data (not a backend contract). */
function nextMockId(prefix: string): string {
  mockCounter += 1;
  return `${prefix}-mock-${mockCounter}`;
}

export interface MockExecutionOptions {
  requestId?: string;
  sessionId?: string;
  providerModel?: string;
  toolCalls?: Array<{ toolName: string; status?: "completed" | "failed"; error?: string | null }>;
  /** If true, the execution ends with a FAILED event instead of COMPLETED. */
  endWithFailure?: boolean;
}

/**
 * Builds the full ordered event sequence for one mocked execution, following
 * the same lifecycle GatewayRouter/Orchestrator emit server-side:
 *   REQUEST_RECEIVED -> EXECUTION_STARTED -> TOOL_EXECUTION* -> COMPLETED | FAILED
 */
export function createMockExecutionEvents(options: MockExecutionOptions = {}): GatewayEvent[] {
  const requestId = options.requestId ?? nextMockId("req");
  const sessionId = options.sessionId ?? nextMockId("sess");
  const providerModel = options.providerModel ?? "mock-provider/mock-model-v1";
  const toolCalls = options.toolCalls ?? [
    { toolName: "web_search" },
    { toolName: "calculator" },
  ];

  const events: GatewayEvent[] = [];
  const baseTime = Date.now() / 1000;
  let t = baseTime;

  events.push({
    event_type: EventLifecycle.REQUEST_RECEIVED,
    request_id: requestId,
    timestamp: t,
    payload: {
      session_id: sessionId,
      messages_count: 1,
    },
  });

  t += 0.05;
  events.push({
    event_type: EventLifecycle.EXECUTION_STARTED,
    request_id: requestId,
    timestamp: t,
    payload: {
      provider_model: providerModel,
    },
  });

  for (const call of toolCalls) {
    t += 0.2;
    const status = call.status ?? "completed";
    events.push({
      event_type: EventLifecycle.TOOL_EXECUTION,
      request_id: requestId,
      timestamp: t,
      payload: {
        request_id: requestId,
        event_type: "tool_called",
        timestamp: t,
        tool_name: call.toolName,
        status,
        session_id: sessionId,
        tool_call_id: nextMockId("call"),
        execution_time_ms: Math.round(50 + Math.random() * 400),
        error: status === "failed" ? (call.error ?? "mock tool failure") : null,
      },
    });
  }

  t += 0.1;
  if (options.endWithFailure) {
    events.push({
      event_type: EventLifecycle.FAILED,
      request_id: requestId,
      timestamp: t,
      payload: {
        error: "mock execution failure",
      },
    });
  } else {
    events.push({
      event_type: EventLifecycle.COMPLETED,
      request_id: requestId,
      timestamp: t,
      payload: {
        status: "success",
      },
    });
  }

  return events;
}