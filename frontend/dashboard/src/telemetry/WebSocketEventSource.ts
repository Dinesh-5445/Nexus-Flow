// Telemetry: WebSocket Event Source (Day 3)
//
// First real (non-mock) TelemetryEventSource implementation. Connects to
// Sayan's now-working `/stream/:execution_id` WebSocket endpoint
// (services/api/src/index.ts) and forwards parsed events to subscribers,
// implementing the same subscribe/close shape MockEventSource already used
// (see EventSource.ts) so consumers don't care which source they're given.
//
// Emits `LiveGatewayEvent` (see liveTypes.ts), not the stricter `GatewayEvent`
// from types.ts — that's the shape the server actually sends today (no
// payload). See liveTypes.ts for the full contract-mismatch note.
//
// Dev note: a direct cross-origin `fetch("http://localhost:3000/execute")`
// from the Vite dev server's origin is blocked by the browser, because
// services/api sends no Access-Control-Allow-Origin header. The WebSocket
// upgrade itself isn't subject to that same-origin fetch restriction, but to
// keep both calls consistent this is meant to be used with relative URLs
// (e.g. "/stream/abc123") routed through the dev proxy configured in
// vite.config.ts, which forwards to http://localhost:3000. That proxy is a
// frontend-only, dev-time workaround; it does not modify services/api. A
// real deployment still needs a CORS/proxy decision from Sayan.

import type { TelemetryEventSource, TelemetryListener } from "./EventSource";
import type { LiveGatewayEvent } from "./liveTypes";
import { isLiveGatewayEvent } from "./liveTypes";

export interface WebSocketEventSourceConfig {
  /** Full ws(s):// URL, or a path (e.g. "/stream/abc123") resolved against the current page origin. */
  url: string;
  /** Called on socket errors or malformed/unparseable messages. Optional. */
  onError?: (error: unknown) => void;
}

export class WebSocketEventSource implements TelemetryEventSource<LiveGatewayEvent> {
  private readonly listeners = new Set<TelemetryListener<LiveGatewayEvent>>();
  private socket: WebSocket | null = null;
  private closed = false;

  constructor(private readonly config: WebSocketEventSourceConfig) {}

  subscribe(listener: TelemetryListener<LiveGatewayEvent>): () => void {
    this.listeners.add(listener);
    this.ensureConnected();
    return () => {
      this.listeners.delete(listener);
    };
  }

  close(): void {
    this.closed = true;
    this.listeners.clear();
    this.socket?.close();
    this.socket = null;
  }

  private ensureConnected(): void {
    if (this.socket !== null || this.closed) {
      return;
    }

    const socket = new WebSocket(this.resolveUrl(this.config.url));
    this.socket = socket;

    socket.addEventListener("message", (evt) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(evt.data as string);
      } catch (err) {
        this.config.onError?.(err);
        return;
      }
      if (!isLiveGatewayEvent(parsed)) {
        this.config.onError?.(
          new Error(`Received malformed event from /stream: ${String(evt.data)}`)
        );
        return;
      }
      for (const listener of this.listeners) {
        listener(parsed);
      }
    });

    socket.addEventListener("error", () => {
      this.config.onError?.(new Error("WebSocket connection error"));
    });
  }

  private resolveUrl(url: string): string {
    if (/^wss?:\/\//i.test(url)) {
      return url;
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const path = url.startsWith("/") ? url : `/${url}`;
    return `${proto}//${window.location.host}${path}`;
  }
}