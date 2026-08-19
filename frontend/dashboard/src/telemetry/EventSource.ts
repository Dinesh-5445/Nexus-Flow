// Telemetry: Event-Consumption Foundation
//
// Defines the shape the frontend uses to *consume* execution events,
// independent of where those events come from. Today the only implementation
// is MockEventSource (mocked events, no real pipeline dependency). Once
// Sayan's WebSocket endpoint (`/stream/:execution_id`) is implemented, a
// WebSocketEventSource can implement this same interface and be swapped in
// without changing any consumer (see useTelemetryEvents.ts).
//
// This mirrors, on the frontend side, the subscribe/publish shape of
// Dinesh's EventStream (src/events/stream.py) — the difference being that
// EventStream.subscribe() hands subscribers only `Event.payload`, while here
// consumers receive the full GatewayEvent envelope (event_type, request_id,
// timestamp, payload), since the dashboard needs to filter/render across
// event types, not just react to one payload shape.

import type { GatewayEvent } from "./types";

export type TelemetryListener = (event: GatewayEvent) => void;

/** Something the frontend can subscribe to for a live sequence of GatewayEvents. */
export interface TelemetryEventSource {
  /**
   * Registers a listener that will be called with each GatewayEvent as it
   * arrives. Returns an unsubscribe function.
   */
  subscribe(listener: TelemetryListener): () => void;

  /** Stops the source (clears timers / closes sockets) and drops all listeners. */
  close(): void;
}