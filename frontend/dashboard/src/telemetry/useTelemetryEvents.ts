// Telemetry: Event-Consumption Hook
//
// Foundation hook for consuming a TelemetryEventSource from React. This is
// intentionally not wired into DashboardLayout/App yet — today's task is the
// consumption foundation, not the full dashboard. Panels can adopt this hook
// (or a selector built on top of it) once the dashboard is ready to render
// live data instead of placeholderData.ts.
//
// Defaults to MockEventSource so it works standalone with no real transport.
// Pass a different `source` (e.g. a future WebSocketEventSource) to swap
// feeds without changing this hook's consumers.

import { useEffect, useMemo, useRef, useState } from "react";
import type { TelemetryEventSource } from "./EventSource";
import { MockEventSource } from "./MockEventSource";
import {
  statusForEvent,
  type ExecutionStatusInfo,
  type GatewayEvent,
} from "./types";

export interface UseTelemetryEventsOptions {
  /** Event source to consume. Defaults to a fresh MockEventSource. */
  source?: TelemetryEventSource;
  /** Caps how many events are retained in state (oldest dropped first). */
  maxEvents?: number;
}

export interface UseTelemetryEventsResult {
  /** All events observed so far, oldest first. */
  events: GatewayEvent[];
  /** Most recent event, if any. */
  latestEvent: GatewayEvent | null;
  /** Derived per-request execution status, keyed by request_id. */
  statusByRequestId: Record<string, ExecutionStatusInfo>;
}

const DEFAULT_MAX_EVENTS = 200;

/**
 * Subscribes to a TelemetryEventSource for the lifetime of the component and
 * accumulates GatewayEvents plus a derived per-request ExecutionStatusInfo.
 */
export function useTelemetryEvents(
  options: UseTelemetryEventsOptions = {}
): UseTelemetryEventsResult {
  const { maxEvents = DEFAULT_MAX_EVENTS } = options;

  // Own a default MockEventSource for the component's lifetime unless the
  // caller supplied one explicitly.
  const ownedSourceRef = useRef<MockEventSource | null>(null);
  const source = useMemo<TelemetryEventSource>(() => {
    if (options.source) {
      return options.source;
    }
    const owned = new MockEventSource();
    ownedSourceRef.current = owned;
    return owned;
  }, [options.source]);

const [events, setEvents] = useState<GatewayEvent[]>([]);
const [statusByRequestId, setStatusByRequestId] = useState<
  Record<string, ExecutionStatusInfo>
>({});

  useEffect(() => {
    const unsubscribe = source.subscribe((event) => {
      setEvents((prev) => {
        const next = [...prev, event];
        return next.length > maxEvents ? next.slice(next.length - maxEvents) : next;
      });

      setStatusByRequestId((prev) => {
        const existing = prev[event.request_id];
        const status = statusForEvent(event.event_type);
        const next: ExecutionStatusInfo = {
          requestId: event.request_id,
          status,
          startedAt: existing?.startedAt ?? event.timestamp,
          endedAt:
            status === "completed" || status === "failed"
              ? event.timestamp
              : existing?.endedAt ?? null,
          error:
            event.event_type === "failed"
              ? event.payload.error
              : existing?.error ?? null,
        };
        return { ...prev, [event.request_id]: next };
      });
    });

    return () => {
      unsubscribe();
      // Only close sources this hook created itself; caller-supplied
      // sources may be shared and are the caller's responsibility to close.
      if (ownedSourceRef.current === source) {
        ownedSourceRef.current.close();
      }
    };
  }, [source, maxEvents]);

  const latestEvent = events.length > 0 ? events[events.length - 1] : null;

  return { events, latestEvent, statusByRequestId };
}