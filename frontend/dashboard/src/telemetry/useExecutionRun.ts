// Telemetry: Execution Run Hook (Day 9)
//
// Starts an execution through the REST/WebSocket surface and exposes its live
// state: POST /execute (submit) + WS /stream/:id and GET /status/:id
// (via useLiveExecution).
//
// Ordering matters: services/api only relays lifecycle events to WebSocket
// clients that are connected when the event is emitted (no buffering/replay),
// and the WS upgrade does not require the execution to exist yet. So the
// stream is opened FIRST and POST /execute is only sent once the socket is
// open; otherwise a fast execution could finish before the dashboard is
// listening and its events would be lost.

import { useCallback, useEffect, useState } from "react";
import { useLiveExecution, type LiveExecutionState } from "./useLiveExecution";
import { getScenario, type ScenarioId } from "./executionScenarios";

/** How long to wait for the event stream to open before giving up. */
const STREAM_OPEN_TIMEOUT_MS = 5000;

export type RunPhase = "idle" | "connecting" | "submitting" | "submitted" | "failed_to_start";

export interface ExecutionRun {
  live: LiveExecutionState;
  phase: RunPhase;
  /** Why the last start attempt failed (stream or POST /execute), if it did. */
  startError: string | null;
  /** True while a start is in flight (stream opening or request being submitted). */
  busy: boolean;
  start: (scenarioId: ScenarioId) => void;
}

interface PendingStart {
  requestId: string;
  scenarioId: ScenarioId;
}

async function submitExecution(requestId: string, scenarioId: ScenarioId): Promise<void> {
  // Relative URL so this goes through the Vite dev proxy (vite.config.ts).
  const res = await fetch("/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: requestId,
      messages: getScenario(scenarioId).messages,
      session_id: "dashboard-live",
    }),
  });

  if (!res.ok) {
    const body: unknown = await res.json().catch(() => ({}));
    const apiError =
      typeof body === "object" && body !== null && "error" in body
        ? (body as { error: unknown }).error
        : undefined;
    throw new Error(
      typeof apiError === "string" ? apiError : `Request failed with status ${res.status}`
    );
  }
}

export function useExecutionRun(): ExecutionRun {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingStart | null>(null);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [startError, setStartError] = useState<string | null>(null);

  const live = useLiveExecution(requestId, { submitted: phase === "submitted" });

  const failStart = useCallback((message: string) => {
    setStartError(message);
    setPending(null);
    setRequestId(null);
    setPhase("failed_to_start");
  }, []);

  // Once the stream is open, submit the execution.
  useEffect(() => {
    if (phase !== "connecting" || !pending) {
      return;
    }
    if (live.connection === "error" || live.connection === "closed") {
      failStart(live.connectionError ?? "Could not open the event stream");
      return;
    }
    if (live.connection !== "open") {
      return;
    }

    const { requestId: id, scenarioId } = pending;
    setPending(null);
    setPhase("submitting");
    submitExecution(id, scenarioId)
      .then(() => setPhase("submitted"))
      .catch((err: unknown) => failStart(err instanceof Error ? err.message : String(err)));
  }, [phase, pending, live.connection, live.connectionError, failStart]);

  // Don't wait on the stream forever.
  useEffect(() => {
    if (phase !== "connecting") {
      return;
    }
    const timer = setTimeout(
      () => failStart("Timed out opening the event stream"),
      STREAM_OPEN_TIMEOUT_MS
    );
    return () => clearTimeout(timer);
  }, [phase, failStart]);

  const busy = phase === "connecting" || phase === "submitting";

  const start = useCallback(
    (scenarioId: ScenarioId) => {
      if (busy) {
        return;
      }
      const id = `req-${Date.now()}`;
      setStartError(null);
      setPending({ requestId: id, scenarioId });
      setPhase("connecting");
      setRequestId(id);
    },
    [busy]
  );

  return { live, phase, startError, busy, start };
}