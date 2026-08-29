// Telemetry: Live Execution Hook (Day 3, status contract finalized Day 4)
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
//
// Day 4: `status` (plus `endedAt`/`error`) now comes from GET
// /status/:execution_id — Sayan's InternalExecutionState, mirroring
// src/state/manager.py's ExecutionState contract — instead of being derived
// locally from the last-seen event via statusForEvent(). That local
// derivation had drifted from the backend's real status vocabulary (see
// liveTypes.ts's LiveExecutionStatus doc comment) and duplicated
// backend-owned business logic on the frontend, which the project's
// architecture rules call out to avoid. The event stream is still consumed
// directly for the raw lifecycle timeline; only the authoritative
// pending/running/completed/failed status is now sourced from /status.

import { useEffect, useRef, useState } from "react";
import { WebSocketEventSource } from "./WebSocketEventSource";
import type { LiveGatewayEvent, LiveExecutionStatus } from "./liveTypes";
import { isLiveExecutionStatus } from "./liveTypes";
import type { ExecutionStatus } from "./types";

export interface LiveExecutionState {
  requestId: string;
  status: ExecutionStatus;
  /** Lifecycle events observed so far, oldest first. */
  events: LiveGatewayEvent[];
  /** Timestamp (seconds, matching the backend's time.time()) of the first observed event. */
  startedAt: number | null;
  /** Timestamp of the most recent observed event. */
  lastEventAt: number | null;
  /** `end_time` from the authoritative status, once execution reaches a terminal state. */
  endedAt: number | null;
  /** `error` from the authoritative status, if the execution failed. */
  error: string | null;
  /** Set when the WebSocket connection itself fails or sends a malformed message. */
  connectionError: string | null;
  /** Set when GET /status/:requestId fails or returns an unexpected shape. */
  statusError: string | null;
}

async function fetchExecutionStatus(requestId: string): Promise<LiveExecutionStatus> {
  // Relative URL so this goes through the Vite dev proxy (vite.config.ts),
  // same reasoning as ExecutionMonitor's POST /execute call.
  const res = await fetch(`/status/${requestId}`);
  if (!res.ok) {
    throw new Error(`GET /status/${requestId} failed with status ${res.status}`);
  }
  const body: unknown = await res.json();
  if (!isLiveExecutionStatus(body)) {
    throw new Error(`GET /status/${requestId} returned an unexpected shape`);
  }
  return body;
}

/**
 * Subscribes to `/stream/:requestId` for as long as a non-null `requestId`
 * is passed, accumulating the raw lifecycle events, and polls the
 * authoritative `/status/:requestId` state whenever a new event arrives.
 * Pass `null` to stay idle (e.g. before an execution has been started).
 */
export function useLiveExecution(requestId: string | null): LiveExecutionState {
  const [events, setEvents] = useState<LiveGatewayEvent[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [status, setStatus] = useState<LiveExecutionStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const sourceRef = useRef<WebSocketEventSource | null>(null);

  useEffect(() => {
    setEvents([]);
    setConnectionError(null);
    setStatus(null);
    setStatusError(null);

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

  // Re-fetch the authoritative status whenever a new lifecycle event arrives.
  // There's no push-based status update from the backend today, so an
  // incoming event is the frontend's only signal that server-side state may
  // have changed; this also fetches once immediately on start (events.length
  // transitions from N/A to 0).
  useEffect(() => {
    if (!requestId) {
      return;
    }
    let cancelled = false;
    fetchExecutionStatus(requestId)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch((err) => {
        if (!cancelled) setStatusError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [requestId, events.length]);

  const startedAt = events.length > 0 ? events[0].timestamp : null;
  const lastEventAt = events.length > 0 ? events[events.length - 1].timestamp : null;

  return {
    requestId: requestId ?? "",
    status: status?.status ?? "pending",
    events,
    startedAt,
    lastEventAt,
    endedAt: status?.end_time ?? null,
    error: status?.error ?? null,
    connectionError,
    statusError,
  };
}