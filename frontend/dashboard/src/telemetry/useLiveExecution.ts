// Telemetry: Live Execution Hook (Day 3)
//
// Consumes a single execution's real event stream from services/api via
// WebSocketEventSource. This is the "start consuming Sayan's working
// REST/WebSocket event stream" half of today's task; ExecutionMonitor.tsx
// (in ../components) is the "minimal execution-status/event view" half.
//
// Deliberately separate from useTelemetryEvents.ts (Day 2), which still
// defaults to MockEventSource / GatewayEvent and remains useful for
// exercising UI against mocked data with no backend dependency. Reconciling
// the two into one hook is a later step, not part of today's scope.

import { useEffect, useMemo, useRef, useState } from "react";
import { WebSocketEventSource } from "./WebSocketEventSource";
import type { LiveGatewayEvent } from "./liveTypes";
import { statusForEvent, type ExecutionStatus } from "./types";

export interface LiveExecutionState {
  requestId: string;
  status: ExecutionStatus;
  /** Lifecycle events observed so far, oldest first. */
  events: LiveGatewayEvent[];
  /** Timestamp (seconds, matching the backend's time.time()) of the first observed event. */
  startedAt: number | null;
  /** Timestamp of the most recent observed event. */
  lastEventAt: number | null;
  connectionError: string | null;
}

/**
 * Subscribes to `/stream/:requestId` for as long as a non-null `requestId`
 * is passed and accumulates the raw lifecycle events plus a derived status.
 * Pass `null` to stay idle (e.g. before an execution has been started).
 */
export function useLiveExecution(requestId: string | null): LiveExecutionState {
  const [events, setEvents] = useState<LiveGatewayEvent[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const sourceRef = useRef<WebSocketEventSource | null>(null);

  useEffect(() => {
    setEvents([]);
    setConnectionError(null);

    if (!requestId) {
      return;
    }

    const source = new WebSocketEventSource({
      url: `/stream/${requestId}`,
      onError: (err) => setConnectionError(err instanceof Error ? err.message : String(err)),
    });
    sourceRef.current = source;

    const unsubscribe = source.subscribe((event) => {
      setEvents((prev) => [...prev, event]);
    });

    return () => {
      unsubscribe();
      source.close();
      sourceRef.current = null;
    };
  }, [requestId]);

  const status: ExecutionStatus = useMemo(() => {
    if (events.length === 0) {
      return "pending";
    }
    return statusForEvent(events[events.length - 1].event_type);
  }, [events]);

  const startedAt = events.length > 0 ? events[0].timestamp : null;
  const lastEventAt = events.length > 0 ? events[events.length - 1].timestamp : null;

  return {
    requestId: requestId ?? "",
    status,
    events,
    startedAt,
    lastEventAt,
    connectionError,
  };
}