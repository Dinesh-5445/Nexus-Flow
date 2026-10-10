# Telemetry / Event-Consumption

Status (Day 9, V1): the dashboard renders live data from Sayan's REST/WebSocket
API end to end. A mock path (`useTelemetryEvents.ts`) is kept for developing UI
against mocked data with no backend.

## Data flow

```text
Dashboard ── WS  /stream/:id  ──▶ lifecycle events (with payloads)
          ── POST /execute    ──▶ starts an execution (202)
          ── GET  /status/:id ──▶ authoritative status (InternalExecutionState)
```

| Dashboard element | Source |
|---|---|
| Execution status, start/end time | `GET /status/:id` (authoritative; not derived from events) |
| Lifecycle timeline, event summaries | `WS /stream/:id` events and their `payload` |
| Request latency | `/status` `end_time − start_time` (API-side clock; includes gateway process startup) |
| Pipeline time | last − first lifecycle event timestamp (Python clock) |
| Event / tool activity | counts over received events; tool time = sum of `execution_time_ms` |
| Watchdog alerts | `payload.watchdog_alert` on `tool_execution` events |
| Execution error | `/status` `error`, else the `failed` event's `payload.error` |

## Files

- `useExecutionRun.ts` — starts an execution. Opens the WebSocket **first**, then
  sends `POST /execute` once the socket is open (services/api relays events only
  to sockets connected at emit time, with no buffering or replay). Fails cleanly
  if the stream can't open (5 s timeout) or `POST /execute` is rejected.
- `useLiveExecution.ts` — per-execution state keyed by `request_id`: events,
  stream connection state, authoritative status. Status is refreshed on every
  event and polled (1.5 s) while non-terminal, so a dropped socket can't leave
  the UI stuck on "pending".
- `WebSocketEventSource.ts` — `TelemetryEventSource` over `/stream/:id`, with
  open/close/error callbacks.
- `liveTypes.ts` — wire shapes actually served today (`LiveGatewayEvent`,
  `LiveExecutionStatus`) plus `StreamConnection`.
- `livePayloads.ts` — structural readers that narrow `payload` (tool, LLM,
  failed, Watchdog alert, …) without casting.
- `liveAdapters.ts` — maps live state to the panel props in `../types.ts`
  (session, events, metrics, alerts). Presentation only.
- `executionScenarios.ts` — request bodies for the dashboard's scenario picker
  (plain success, success with tool call, failure). See below.
- `types.ts`, `mockEvents.ts`, `MockEventSource.ts`, `useTelemetryEvents.ts` —
  schema-accurate representation and mock path (Day 2). Not used by the live path.

## Watchdog alerts

The Watchdog does not publish its own event. It annotates the triggering
`tool_execution` payload in place (`payload.watchdog_alert = { request_id,
anomaly_type, tool_name, count }`, `src/watchdog/detector.py`), and
`src/main.py` serializes the event after payload subscribers have run, so the
annotation reaches the browser on that same event. The alert has no timestamp of
its own; the dashboard shows the carrying event's timestamp.

With V1's `MockProvider` an execution makes at most one tool call, below the
default threshold of 5, so alerts don't occur in a live run through the API.
The alert path was validated by feeding real `EventStream` + `Watchdog` output
(same wiring as `src/main.py`) through `liveAdapters.ts`.

## Scenario picker

The scenarios are validation inputs, not API contract. They depend on:
`MockProvider` returning a calculator tool call when the last message contains
"calculate", and the Orchestrator building `LLMMessage(**msg)` so a message
without `content` raises and the Gateway publishes `failed`. If either changes,
update `executionScenarios.ts`.

## Known contract notes

- `GET /status/:id` does not include `error` for a failed execution
  (`emitEvent` in `services/api/src/index.ts` sets status and `end_time` but
  doesn't copy `payload.error` into the state). The dashboard falls back to the
  `failed` event's payload. Worth raising with Sayan.
- `ToolResult.to_event_payload()` nests its own `request_id`, `timestamp` and
  `event_type` inside the payload (now `"tool_execution"`, previously
  `"tool_called"`), duplicating the outer envelope. Kept as-is.
- `services/api` sends no CORS headers; the dashboard relies on the Vite dev
  proxy (`vite.config.ts`). A real deployment still needs a CORS/proxy decision
  from Sayan.

## Out of scope

- Aggregate / cross-execution telemetry (throughput over time, history) — no
  endpoint exists; the dashboard tracks one execution at a time.
- Automatic WebSocket reconnect and event replay — needs buffering in
  `services/api`.