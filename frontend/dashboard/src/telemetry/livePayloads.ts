// Telemetry: Live Payload Readers (Day 9)
//
// Structural readers for the `payload` of events relayed by services/api.
// `LiveGatewayEvent.payload` is `unknown` (see liveTypes.ts); these functions
// narrow it field-by-field to the payload shapes the Python producers emit
// today (documented in types.ts), returning null/undefined for anything that
// doesn't match instead of casting.
//
// Watchdog alerts: Koushik's Watchdog does not publish a separate event. It
// annotates the triggering tool_execution payload in place
// (`payload["watchdog_alert"] = alert`, src/watchdog/detector.py), and
// src/main.py serializes the full Event after payload subscribers have run,
// so the annotation reaches the browser on the same tool_execution event as
// `payload.watchdog_alert = { request_id, anomaly_type, tool_name, count }`.

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function str(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export interface ToolExecutionSummary {
  toolName: string;
  status: string | null;
  executionTimeMs: number | null;
  error: string | null;
}

/** tool_execution payload (ToolResult.to_event_payload, src/tools/base.py). */
export function readToolPayload(payload: unknown): ToolExecutionSummary | null {
  if (!isRecord(payload)) return null;
  const toolName = str(payload.tool_name);
  if (toolName === null) return null;
  return {
    toolName,
    status: str(payload.status),
    executionTimeMs: num(payload.execution_time_ms),
    error: str(payload.error),
  };
}

export interface WatchdogAlertSummary {
  anomalyType: string;
  toolName: string | null;
  count: number | null;
}

/** `payload.watchdog_alert` as annotated by src/watchdog/detector.py. */
export function readWatchdogAlert(payload: unknown): WatchdogAlertSummary | null {
  if (!isRecord(payload)) return null;
  const alert = payload.watchdog_alert;
  if (!isRecord(alert)) return null;
  const anomalyType = str(alert.anomaly_type);
  if (anomalyType === null) return null;
  return {
    anomalyType,
    toolName: str(alert.tool_name),
    count: num(alert.count),
  };
}

/** failed payload (`{ error }`, src/gateway/router.py). */
export function readFailedError(payload: unknown): string | null {
  return isRecord(payload) ? str(payload.error) : null;
}

/** request_received payload (src/gateway/router.py). */
export function readRequestReceived(
  payload: unknown
): { sessionId: string | null; messagesCount: number | null } | null {
  if (!isRecord(payload)) return null;
  return { sessionId: str(payload.session_id), messagesCount: num(payload.messages_count) };
}

/** execution_started payload (src/orchestration/executor.py). */
export function readExecutionStarted(payload: unknown): { model: string | null } | null {
  return isRecord(payload) ? { model: str(payload.provider_model) } : null;
}

/** llm_execution payload (src/orchestration/executor.py). `usage` is untyped upstream. */
export function readLlmPayload(
  payload: unknown
): { model: string | null; totalTokens: number | null } | null {
  if (!isRecord(payload)) return null;
  const usage = payload.usage;
  return {
    model: str(payload.model),
    totalTokens: isRecord(usage) ? num(usage.total_tokens) : null,
  };
}

/** completed payload (`{ status: "success" }`, src/gateway/router.py). */
export function readCompletedStatus(payload: unknown): string | null {
  return isRecord(payload) ? str(payload.status) : null;
}