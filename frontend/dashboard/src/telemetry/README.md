# Telemetry / Event-Consumption Foundation

Status: **foundation only**, not wired into the dashboard UI yet.

## Scope of this folder (today)

- Define how execution events and execution status are represented on the
  frontend (`types.ts`), modeled directly on the current backend contract:
  - `src/events/schema.py` (Event envelope + `EventLifecycle`) — Dinesh
  - `src/gateway/router.py` (`request_received` / `completed` / `failed` payloads) — Dinesh
  - `src/orchestration/executor.py` (`execution_started` payload) — Dinesh
  - `src/tools/base.py` (`ToolResult.to_event_payload`, the `tool_execution` payload
    also consumed by the Watchdog) — Jyothi
  - `src/state/manager.py` (`ExecutionState.status` values) — Dinesh
- Define a transport-agnostic consumption interface (`EventSource.ts`).
- Provide a mocked event feed (`mockEvents.ts`, `MockEventSource.ts`) so the
  above can be exercised with **no dependency on the real execution
  pipeline** — `services/api` (Sayan) does not yet implement `/execute` or
  `/stream/:execution_id`.
- Provide a React hook (`useTelemetryEvents.ts`) as the consumption
  foundation UI code will eventually build on.

## Explicitly out of scope (today)

- Wiring this into `App.tsx` / `DashboardLayout.tsx` / the existing panel
  components. Those still use `../types.ts` and `../data/placeholderData.ts`
  (looser placeholder shapes) — reconciling the two is a follow-up, not part
  of today's task.
- Any real WebSocket/REST connection. That depends on Sayan's `/stream/:id`
  implementation.
- Visualizing tool-call sequences for the Watchdog's anomaly signals
  (repeated calls, timeouts, loops) — that's dashboard/alert-visualization
  work for a later session.

## Known contract note

`ToolResult.to_event_payload()` (src/tools/base.py) nests its own
`request_id`, `timestamp`, and a literal `event_type: "tool_called"` inside
the `tool_execution` event's payload — separate from, and inconsistent with,
the outer envelope's `event_type` (`EventLifecycle.TOOL_EXECUTION`). This
frontend representation (`ToolExecutionPayload` in `types.ts`) mirrors the
payload exactly as produced rather than silently normalizing it. Worth
raising with Dinesh/Jyothi/Koushik since the Watchdog also relies on this
shape.

## Swapping in a real feed later

`useTelemetryEvents` takes an optional `source: TelemetryEventSource`. Once
Sayan's WebSocket endpoint exists, a `WebSocketEventSource` implementing the
same `subscribe`/`close` interface as `MockEventSource` can be passed in
directly — no changes needed to the hook or its future consumers.