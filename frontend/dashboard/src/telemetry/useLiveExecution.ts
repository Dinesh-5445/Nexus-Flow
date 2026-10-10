// Telemetry: Live Execution Hook (Day 3, status contract Day 4, hardened Day 9)
//
// Consumes a single execution's real event stream from services/api via
// WebSocketEventSource and tracks its authoritative status from
// GET /status/:execution_id (Sayan's InternalExecutionState, mirroring
// src/state/manager.py's ExecutionState).
//
// Day 4 contract (unchanged): `status`, `endedAt` come from /status, not from
// a local derivation over event types — that would duplicate backend-owned
// logic on the frontend.
//
// Day 9 changes:
//  - Exposes the WebSocket `connection` state so callers can open the stream
//    BEFORE submitting POST /execute (services/api only relays events to
//    sockets connected at emit time and does not buffer/replay).
//  - Status is refreshed on every new event AND polled while the execution is
//    non-terminal (Sayan's documented polling fallback), so a dropped socket or
//    a missed event can't leave the dashboard stuck on "pending".
//  - All per-execution state is keyed by request_id, so switching to a new
//    execution never shows (or lets a late response write) the previous
//    execution's data.
//  - `error` falls back to the `failed` event's payload.error: services/api
//    records a failed status but does not copy the error message into
//    GET /status (verified against the running service), while the failed
//    event itself carries it.

import { useCallback, useEffect, useRef, useState } from "react";
import { WebSocketEventSource } from "./WebSocketEventSource";
import type { LiveGatewayEvent, LiveExecutionStatus, StreamConnection } from "./liveTypes";
import { isLiveExecutionStatus } from "./liveTypes";
import type { ExecutionStatus } from "./types";
import { readFailedError } from "./livePayloads";

/** How often the authoritative status is re-fetched while non-terminal. */
const STATUS_POLL_MS = 1500;

export interface LiveExecutionState {
  requestId: string;
  status: ExecutionStatus;
  /** Lifecycle events observed so far, oldest first. */
  events: LiveGatewayEvent[];
  /** `start_time` from the authoritative status (API-side clock), once fetched. */
  startedAt: number | null;
  /** Timestamp (seconds, Python clock) of the first observed event. */
  firstEventAt: number | null;
  /** Timestamp of the most recent observed event. */
  lastEventAt: number | null;
  /** `end_time` from the authoritative status, once execution reaches a terminal state. */
  endedAt: number | null;
  /** Execution error: `/status` error, else the `failed` event's payload.error. */
  error: string | null;
  /** WebSocket connection state for /stream/:requestId. */
  connection: StreamConnection;
  /** Set when the WebSocket connection itself fails or sends a malformed message. */
  connectionError: string | null;
  /** Set when GET /status/:requestId fails or returns an unexpected shape. */
  statusError: string | null;
}

export interface UseLiveExecutionOptions {
  /**
   * Whether POST /execute has been accepted. /status is only requested once
   * this is true (or an event has already arrived), because the API returns
   * 404 for an execution_id it hasn't seen yet. Defaults to true.
   */
  submitted?: boolean;
}

interface Tracked {
  id: string | null;
  events: LiveGatewayEvent[];
  connection: StreamConnection;
  connectionError: string | null;
  status: LiveExecutionStatus | null;
  statusError: string | null;
}

function freshFor(id: string | null): Tracked {
  return {
    id,
    events: [],
    connection: id === null ? "idle" : "connecting",
    connectionError: null,
    status: null,
    statusError: null,
  };
}

export function isTerminalStatus(status: ExecutionStatus | undefined): boolean {
  return status === "completed" || status === "failed";
}

async function fetchExecutionStatus(requestId: string): Promise<LiveExecutionStatus> {
  // Relative URL so this goes through the Vite dev proxy (vite.config.ts).
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
 * is passed, accumulating the raw lifecycle events, and keeps the
 * authoritative `/status/:requestId` state fresh. Pass `null` to stay idle.
 */
export function useLiveExecution(
  requestId: string | null,
  options: UseLiveExecutionOptions = {}
): LiveExecutionState {
  const { submitted = true } = options;
  const [tracked, setTracked] = useState<Tracked>(() => freshFor(null));
  const statusSeq = useRef(0);

  // State recorded for a different request_id is never shown: until the
  // effect below resets it, the view is derived as a fresh state.
  const view = tracked.id === requestId ? tracked : freshFor(requestId);

  const patch = useCallback((id: string, update: (t: Tracked) => Tracked) => {
    setTracked((prev) => (prev.id === id ? update(prev) : prev));
  }, []);

  useEffect(() => {
    setTracked(freshFor(requestId));

    if (!requestId) {
      return;
    }
    const id = requestId;

    const source = new WebSocketEventSource({
      url: `/stream/${id}`,
      onOpen: () => patch(id, (t) => ({ ...t, connection: "open" })),
      onClose: () =>
        patch(id, (t) => ({ ...t, connection: t.connection === "error" ? "error" : "closed" })),
      onSocketError: (err) =>
        patch(id, (t) => ({ ...t, connection: "error", connectionError: err.message })),
      onError: (err) =>
        patch(id, (t) => ({
          ...t,
          connectionError: err instanceof Error ? err.message : String(err),
        })),
    });

    const unsubscribe = source.subscribe((event) => {
      patch(id, (t) => ({ ...t, events: [...t.events, event] }));
    });

    return () => {
      unsubscribe();
      source.close();
    };
  }, [requestId, patch]);

  const refreshStatus = useCallback(
    async (id: string) => {
      const seq = ++statusSeq.current;
      try {
        const next = await fetchExecutionStatus(id);
        // Drop responses that were superseded by a newer request.
        if (seq === statusSeq.current) {
          patch(id, (t) => ({ ...t, status: next, statusError: null }));
        }
      } catch (err) {
        if (seq === statusSeq.current) {
          patch(id, (t) => ({
            ...t,
            statusError: err instanceof Error ? err.message : String(err),
          }));
        }
      }
    },
    [patch]
  );

  const eventCount = view.events.length;
  const canFetchStatus = requestId !== null && (submitted || eventCount > 0);
  const terminal = isTerminalStatus(view.status?.status);

  // Re-fetch the authoritative status whenever a new lifecycle event arrives
  // (and once as soon as the request has been submitted).
  useEffect(() => {
    if (requestId && canFetchStatus) {
      void refreshStatus(requestId);
    }
  }, [requestId, canFetchStatus, eventCount, refreshStatus]);

  // Polling fallback while the execution is non-terminal.
  useEffect(() => {
    if (!requestId || !canFetchStatus || terminal) {
      return;
    }
    const timer = setInterval(() => void refreshStatus(requestId), STATUS_POLL_MS);
    return () => clearInterval(timer);
  }, [requestId, canFetchStatus, terminal, refreshStatus]);

  const failedEvent = view.events.find((e) => e.event_type === "failed");
  const firstEventAt = eventCount > 0 ? view.events[0].timestamp : null;
  const lastEventAt = eventCount > 0 ? view.events[eventCount - 1].timestamp : null;

  return {
    requestId: requestId ?? "",
    status: view.status?.status ?? "pending",
    events: view.events,
    startedAt: view.status?.start_time ?? null,
    firstEventAt,
    lastEventAt,
    endedAt: view.status?.end_time ?? null,
    error: view.status?.error ?? (failedEvent ? readFailedError(failedEvent.payload) : null),
    connection: view.connection,
    connectionError: view.connectionError,
    statusError: view.statusError,
  };
}