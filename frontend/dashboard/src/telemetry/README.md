# Telemetry / Event-Consumption Foundation

Status: mock event-consumption foundation (`useTelemetryEvents.ts`) plus a
real live-execution path (`useLiveExecution.ts`) wired to Sayan's working
REST/WebSocket API. Rendered separately via `ExecutionMonitor.tsx`
(`../components`) — not yet merged into `DashboardLayout.tsx`'s panels.

## Two representations, on purpose

- `types.ts` — the schema-accurate representation modeled directly on
  Dinesh's Python contract (Event envelope + `EventLifecycle`, per-lifecycle
  payloads, `ExecutionState.status` values). Used by the mock path.
- `liveTypes.ts` — the representation of what `services/api` (Sayan) actually
  sends/returns *today* over the wire: `LiveGatewayEvent` (events with no
  `payload`, from `/stream/:execution_id`) and `LiveExecutionStatus`
  (`InternalExecutionState`, from `GET /status/:execution_id`). Kept separate
  from `types.ts` rather than forcing the live wire shape into the stricter
  schema-accurate union — see the contract-mismatch notes in that file.

## Mock path (`useTelemetryEvents.ts`)

- Consumes `MockEventSource` (`mockEvents.ts`, `MockEventSource.ts`) via the
  transport-agnostic `EventSource.ts` interface, with a `statusForEvent()`
  status derived locally from `types.ts`'s `GatewayEvent`s.
- Exists to exercise UI against mocked data with **no dependency on the real
  execution pipeline**. Not wired into `useLiveExecution.ts` or
  `ExecutionMonitor.tsx`.

## Live path (`useLiveExecution.ts`, Day 3–4)

- Subscribes to `/stream/:execution_id` via `WebSocketEventSource` for the
  raw lifecycle event timeline.
- Status, end time, and error come from `GET /status/:execution_id`
  (Sayan's `InternalExecutionState`, mirroring `src/state/manager.py`'s
  `ExecutionState`) — fetched on every new event — rather than being
  re-derived on the frontend from the last-seen event type. An earlier
  version of this hook did that local derivation with `statusForEvent()`;
  it's kept in `types.ts` for the mock path but is no longer used for live
  status, since it had drifted from the backend's real
  pending/running/completed/failed transitions and duplicated backend-owned
  logic on the frontend.
- `ExecutionMonitor.tsx` (`../components`) is the minimal view built on this
  hook: execution ID, authoritative status, total duration once terminal,
  execution error, ordered lifecycle events, and stream/status connection
  errors.

## Explicitly out of scope

- Wiring either path into `App.tsx` / `DashboardLayout.tsx` / the existing
  panel components. Those still use `../types.ts` and
  `../data/placeholderData.ts` (looser placeholder shapes) — reconciling the
  two is a follow-up, not part of today's task.
- Rendering event payloads in `ExecutionMonitor` — the live stream doesn't
  send any today (see `liveTypes.ts`).
- Visualizing tool-call sequences for the Watchdog's anomaly signals
  (repeated calls, timeouts, loops) — that's dashboard/alert-visualization
  work for a later session.

## Known contract notes

- `ToolResult.to_event_payload()` (src/tools/base.py) nests its own
  `request_id`, `timestamp`, and a literal `event_type: "tool_called"` inside
  the `tool_execution` event's payload — separate from, and inconsistent
  with, the outer envelope's `event_type` (`EventLifecycle.TOOL_EXECUTION`).
  This frontend representation (`ToolExecutionPayload` in `types.ts`) mirrors
  the payload exactly as produced rather than silently normalizing it. Worth
  raising with Dinesh/Jyothi/Koushik since the Watchdog also relies on this
  shape.
- `services/api`'s `simulateExecution()` still emits every lifecycle event
  with no `payload` (see `liveTypes.ts`), so `LiveGatewayEvent.payload` stays
  optional/untyped rather than the stricter `GatewayEvent` union in
  `types.ts`. Worth raising with Sayan/Dinesh.