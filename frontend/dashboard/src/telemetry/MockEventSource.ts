// Telemetry: Mock Event Source
//
// Temporary TelemetryEventSource implementation used until Sayan's
// WebSocket endpoint exists. Replays mocked execution event sequences on a
// timer so consumers (useTelemetryEvents.ts) experience the same "events
// arrive one at a time" shape they'll get from a real WebSocket later.
//
// Swap-out plan: a future WebSocketEventSource implementing the same
// TelemetryEventSource interface can replace this with zero changes to
// consumers. This class should be deleted (not extended) once that exists.

import type { TelemetryEventSource, TelemetryListener } from "./EventSource";
import { createMockExecutionEvents, type MockExecutionOptions } from "./mockEvents";
import type { GatewayEvent } from "./types";

export interface MockEventSourceConfig {
  /** Delay in ms between emitted events. Default 400ms. */
  intervalMs?: number;
  /** Options for the single mocked execution this source will replay. */
  execution?: MockExecutionOptions;
}

export class MockEventSource implements TelemetryEventSource {
  private readonly listeners = new Set<TelemetryListener>();
  private readonly queue: GatewayEvent[];
  private readonly intervalMs: number;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private cursor = 0;
  private closed = false;

  constructor(config: MockEventSourceConfig = {}) {
    this.intervalMs = config.intervalMs ?? 400;
    this.queue = createMockExecutionEvents(config.execution);
  }

  subscribe(listener: TelemetryListener): () => void {
    this.listeners.add(listener);
    this.ensureStarted();
    return () => {
      this.listeners.delete(listener);
    };
  }

  close(): void {
    this.closed = true;
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.listeners.clear();
  }

  private ensureStarted(): void {
    if (this.timer !== null || this.closed || this.cursor >= this.queue.length) {
      return;
    }
    this.scheduleNext();
  }

  private scheduleNext(): void {
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.closed || this.cursor >= this.queue.length) {
        return;
      }
      const event = this.queue[this.cursor];
      this.cursor += 1;
      for (const listener of this.listeners) {
        listener(event);
      }
      if (this.cursor < this.queue.length) {
        this.scheduleNext();
      }
    }, this.intervalMs);
  }
}