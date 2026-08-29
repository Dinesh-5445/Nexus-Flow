# Engineering Log

This file records meaningful implementation and development progress.
*Use `experimental_log.md` for architectural decisions, assumptions, and experiments.*

## Entries

### Date: 2026-08-15 — Repository & Architecture Setup

* **Repository Setup:**

  * Established the initial repository structure across `src/`, `services/`, `frontend/`, `tests/`, `docs/`, `logs/`, and `reference/`.
  * Added architecture documentation and technical integration contracts.
  * Established Git workflow guidelines and `CONTRIBUTION_GUIDE.md`.

---

### Date: 2026-08-16 — Day 1 Foundation

* **Dinesh — Gateway / Orchestration:**

  * Implemented `src/gateway/router.py` with the initial `GatewayRouter.handle_request()` skeleton.
  * Implemented `src/orchestration/executor.py` with the initial `Orchestrator.execute_flow()` skeleton.
  * Established the initial Gateway → Orchestrator execution structure.
  * Pathway, event, and state modules remained as initial structures pending Day 2 implementation.

* **Jyothi — LLM / Provider Abstraction / Tool Execution:**

  * Implemented the provider abstraction layer:

    * `src/providers/base.py`
    * `src/providers/mock_provider.py`
  * Added `BaseLLMProvider`, `LLMMessage`, `LLMResponse`, `ToolCall`, and `ProviderConfig`.
  * Implemented the tool execution engine:

    * `src/tools/base.py`
    * `src/tools/registry.py`
    * `src/tools/executor.py`
    * `src/tools/builtin.py`
  * Added `BaseTool`, `ToolRegistry`, `ToolExecutor`, `ToolResult`, `CalculatorTool`, and `EchoTool`.
  * Added Watchdog-compatible event formatting through `ToolResult.to_event_payload()`.
  * Added provider and tool tests.

* **Koushik — Watchdog / Anomaly Detection:**

  * Implemented the initial `Watchdog` prototype in `src/watchdog/detector.py`.
  * Added repeated tool-call detection with an initial threshold of 5 calls.
  * Documented initial monitoring signals in `docs/watchdog/monitoring-signals.md`.
  * Merged the Watchdog foundation PR.

* **Sayan — REST / WebSocket API:**

  * Initialized the Node.js + TypeScript API service under `services/api`.
  * Added Express and WebSocket (`ws`) infrastructure.
  * Implemented initial `/health`, `/execute`, `/status/:execution_id`, and WebSocket `/stream/:execution_id` endpoints.
  * `/execute` and `/status/:execution_id` remain integration stubs pending Gateway integration.


* **Harshit — Frontend / Dashboard / Telemetry:**

  * Scaffolded the dashboard as a Vite + React + TypeScript project under `frontend/dashboard/`.
  * Implemented `App.tsx`, `DashboardLayout.tsx`, and four panel components (`SessionPanel`, `EventStreamPanel`, `MetricsPanel`, `AlertsPanel`).
  * Defined intentionally loose placeholder types (`types.ts`) and local `placeholderData.ts`, since no API contract or event schema existed yet at Day 1.
  * Chat client (`frontend/client/`) remains unstarted.

---



### Date: 2026-08-17 / 2026-08-18 — Day 2 Gateway, Event Contract & Subsystem Compatibility

* **Dinesh — Gateway / Orchestration:**

  * Established the first stable Gateway/Event integration contract and lifecycle definitions (`src/events/schema.py`).
  * Implemented in-memory `EventStream` with `subscribe()` payload dispatch seam (`src/events/stream.py`).
  * Implemented execution state management via `StateManager` (`src/state/manager.py`).
  * Added `GatewayRequest` and `GatewayResponse` models (`src/gateway/models.py`) and `GatewayRouter` (`src/gateway/router.py`).
  * Implemented the Gateway → Orchestrator → Provider/Tool execution flow (`src/orchestration/executor.py`).
  * Added Gateway/Orchestration and EventStream/Watchdog integration tests (`tests/test_gateway_orchestration.py`, `tests/test_eventstream_watchdog_integration.py`).

* **Jyothi — LLM / Provider Abstraction / Tool Execution:**

  * Performed comprehensive Day 2 compatibility audit of provider abstraction (`src/providers/`) and tool execution subsystem (`src/tools/`) against Dinesh's Gateway/Event contract.
  * Verified full compatibility of `BaseLLMProvider`, `MockProvider`, `ToolExecutor`, `ToolRegistry`, and `ToolResult.to_event_payload()`.
  * Confirmed that zero provider/tool code modifications were necessary; existing interfaces seamlessly fulfill all Gateway, Orchestrator, and Watchdog requirements.
  * Validated the full repository test suite with all 28 tests passing.

* **Koushik — Watchdog / Anomaly Detection:**

  * Verified Watchdog prototype (`src/watchdog/detector.py`) integration with `EventStream` via the new subscriber dispatch seam.
  * Confirmed reception of `tool_called` payloads produced by `ToolResult.to_event_payload()`.
  * Validated repeated tool-call anomaly detection and request isolation across unit and integration tests (`tests/test_watchdog.py`, `tests/test_eventstream_watchdog_integration.py`).

* **Sayan — REST / WebSocket API:**

  * Maintained REST / WebSocket API foundation under `services/api`.
  * Integration with Python Gateway core remains pending Day 3 against the finalized `GatewayRequest` / `GatewayResponse` models.


* **Harshit — Frontend / Dashboard / Telemetry:**

  * Dashboard/telemetry scaffolding held stable during Day 2 while Dinesh's Gateway/Event contract stabilized — no changes made against a moving target.
  * `services/telemetry/` (Java/Node alert-aggregation service) not yet started; scoped for after the watchdog alert format and event pipeline are finalized.

---

---

### Date: 2026-08-19 — Day 2 (Harshit): Telemetry Event-Consumption Foundation

* **Harshit — Frontend / Dashboard / Telemetry:**

  * Added `frontend/dashboard/src/telemetry/` — a schema-accurate representation of execution events/status, modeled directly on Dinesh's finalized contract (`src/events/schema.py`, `src/gateway/router.py`, `src/orchestration/executor.py`, `src/tools/base.py`, `src/state/manager.py`).
  * Implemented `EventSource` (transport-agnostic subscribe/close interface), `MockEventSource` (mocked events only, no dependency on the real execution pipeline), and a `useTelemetryEvents` React consumption hook with derived per-request execution status.
  * Flagged an existing contract inconsistency in `ToolResult.to_event_payload()` — the payload's nested `event_type: "tool_called"` conflicts with the outer `EventLifecycle.TOOL_EXECUTION` — for Dinesh/Jyothi/Koushik to resolve.
  * Verified via `tsc --noEmit` (0 errors on the dashboard project) and an isolated runtime smoke test of the mock event sequence, payload shapes, and replay order — all assertions passed.
  * Not yet wired into `DashboardLayout`/panels — that integration step still depends on Sayan's `/stream/:execution_id` (or a decision to wire mocked data into panels first).

* **Sayan — REST / WebSocket API:**

  * Added `api/src/types.ts` — a schema-accurate TypeScript representation of Gateway contracts (`EventLifecycle`, `ExecutionEvent`, `GatewayRequest`, `GatewayResponse`), strictly aligned with Dinesh's event schema and Unix timestamp conventions (`time.time()`).
  * Implemented `POST /execute` (payload validation, mock `202 Accepted` response with `stream_url`), `GET /status/:execution_id` (polling fallback), and `simulateExecution` (mock step execution engine emitting events every 500ms).
  * Implemented WebSocket upgrade handler for `/stream/:execution_id` with per-request client connection tracking (`streamClients` Map) and automatic client cleanup on close.
  * Built `emitEvent` broadcaster to update in-memory `executionStatus` state and stream formatted JSON events to open WebSocket connections in real time.
  * Verified via Postman (HTTP + WebSocket client), `wscat`, and `tsc --noEmit` — validated end-to-end request handling, live event streaming order, and status polling.
  * Unblocked Harshit to wire the telemetry pipeline directly into `/stream/:execution_id`.

---

### Date: 2026-08-20 — Day 3: Provider / Tool & Gateway Orchestration Integration Verification

* **Dinesh — Gateway / Orchestration:**

  * Connected Gateway core (`src/gateway/router.py`) and Orchestrator (`src/orchestration/executor.py`) to the provider abstraction layer and tool execution engine.
  * Replaced mock execution point with the real Provider (`provider.generate()`) and Tool Executor (`tool_executor.execute_tool_call()`) execution path.
  * Verified lifecycle event emission (`REQUEST_RECEIVED` → `EXECUTION_STARTED` → `TOOL_EXECUTION` → `COMPLETED`/`FAILED`).
  * Maintained deferred status for Pathway streaming to prioritize core stability.

* **Jyothi — LLM / Provider Abstraction / Tool Execution:**

  * Verified end-to-end integration of provider abstraction (`src/providers/`) and tool execution subsystem (`src/tools/`) with Dinesh's Gateway/Orchestrator execution flow.
  * Verified message normalization (`LLMMessage`), OpenAPI schema generation (`ToolRegistry.get_schemas()`), and tool execution result formatting (`ToolResult.to_event_payload()`).
  * Confirmed that existing provider and tool implementations are 100% compatible out-of-the-box with zero code changes required.
  * Validated full test suite with all 28 tests passing.

* **Koushik — Watchdog / Anomaly Detection:**

  * Verified Watchdog (`src/watchdog/detector.py`) integration receiving `tool_called` event payloads emitted during live Gateway → Orchestrator → Tool execution via `EventStream.publish()`.
  * Validated repeated tool-call anomaly detection on stream-dispatched tool execution events without blocking the main orchestration flow.

* **Sayan — REST / WebSocket API:**

  * Maintained Node.js + TypeScript REST and WebSocket services under `services/api`.
  * Integration with Python Gateway core remains pending Day 3/Day 4.

* **Harshit — Frontend / Dashboard / Telemetry:**

  * Maintained telemetry event-consumption module (`frontend/dashboard/src/telemetry/`).
  * Wiring into dashboard UI panels pending live WebSocket connection from API layer.

### Current Status

* Gateway and orchestration foundation: **Integrated & Validated**
* Event schema and lifecycle: **Implemented & Validated**
* Execution state management: **Implemented & Validated**
* Provider abstraction & Tool execution: **Integrated, Fully Compatible & Validated (28/28 tests passing)**
* EventStream → Watchdog dispatch seam: **Integrated & Validated**
* Pathway event-stream integration: **Deferred (Post-Core Stabilization)**
* REST/WebSocket Gateway integration: **In Progress / Pending Python Integration**
* Telemetry event representation & consumption: **Implemented & Validated (Harshit)**
* Dashboard UI integration: **Pending Live Stream Wiring**
* End-to-end Gateway-Provider-Tool-Watchdog flow: **Verified & Operational**




### Date: 2026-08-20 — Day 3 Gateway / Orchestration Flow

* **Dinesh — Gateway / Orchestration:**

  * Connected the GatewayRouter and Orchestrator to the provider/tool interfaces (MockProvider, ToolExecutor) via a clean Python execution entry point (src/main.py).
  * Replaced the mock execution flow with a real provider/tool execution path executing entirely within the Gateway boundary.
  * Resolved the 	ool_called vs 	ool_execution contract inconsistency between the Gateway event envelope and the ToolResult payload schema.
  * Validated that Watchdog continues to receive and process events through the EventStream payload subscriber seam.
  * Verified Gateway/Orchestration failure handling, and execution output tests.

### Date: 2026-08-27 — Day 4 Foundation & Flow Verification

* **Dinesh — Gateway / Orchestration:**
  * Verified Gateway → Orchestrator → Provider/Tool execution flow using existing interfaces.
  * Verified lifecycle events: `REQUEST_RECEIVED` → `EXECUTION_STARTED` → `TOOL_EXECUTION` → `COMPLETED` / `FAILED`.
  * Stabilized Gateway/Event/State contracts.
  * Isolated `tests/test_provider_tools_flow.py` from external subsystem dependencies.
  * Validated Gateway/Orchestration failure handling and execution output.

* **Jyothi — LLM / Provider Abstraction / Tool Execution:**
  * Verified provider abstraction (`src/providers/`) and tool execution subsystem (`src/tools/`) against Dinesh's stabilized Gateway → Orchestrator execution flow.
  * Confirmed 100% contract compatibility; zero production code changes needed.
  * Validated all 3 required execution scenarios: Success case (text-only prompt), Tool execution case (tool call generation, execution timing, and event formatting), and Failure cases (arithmetic runtime errors, unregistered tools, invalid arguments, and provider exceptions).
  * Expanded `tests/test_provider_tools_flow.py` with comprehensive integration tests covering all success and failure paths. Full test suite passing (38/38 tests).

* **Koushik — Watchdog / Anomaly Detection:**
  * Connected Watchdog (`src/watchdog/detector.py`) to live execution events via `attach_to_event_stream()` subscribing to `EventStream`.
  * Validated real execution integration tests in `tests/test_watchdog.py` verifying live event processing, repeated tool call alert generation, and request isolation.

* **Sayan — REST / WebSocket API:**
  * Checked `src/gateway/models.py` and `src/events/schema.py` for changes since Day 2 — none found (verified via commit history), so `GatewayRequest`/`GatewayResponse`/`Event` alignment remains accurate.
  * Found `src/state/manager.py` defines an `ExecutionState` contract (`request_id`, `status: 'pending'|'running'|'completed'|'failed'`, `start_time`, `end_time`, `error`) that `/status/:execution_id` did not match — it was returning internal `EventLifecycle` values instead of the real state vocabulary.
  * Added `InternalExecutionState` to `types.ts` and a mapping function (`toExecutionStateStatus`) from internal lifecycle events to the real `pending`/`running`/`completed`/`failed` states.
  * Updated `/execute` and `/status/:execution_id` to track and return `start_time`/`end_time`/`status` consistent with `ExecutionState`.
  * Verified end-to-end via Postman: `/execute` → `202` mocked response, `/status` correctly transitions `pending` → `completed` with populated timestamps.
  * No new endpoints or cross-process architecture introduced.

* **Harshit — Frontend / Dashboard / Telemetry:**
  * Implemented live telemetry execution monitoring in `frontend/dashboard/` (`ExecutionMonitor.tsx`, `WebSocketEventSource.ts`, `liveTypes.ts`, `useLiveExecution.ts`).
  * Connected live telemetry hook to dashboard layout and configured Vite dev server proxy.

### Date: 2026-08-28 — Day 4 (Harshit): Telemetry Status Contract Alignment

* **Harshit — Frontend / Dashboard / Telemetry:**
  * Finalized the live execution-status representation: `useLiveExecution.ts` now sources `status`/`end_time`/`error` from Sayan's `GET /status/:execution_id` (`InternalExecutionState`, mirroring `src/state/manager.py`'s `ExecutionState`) instead of re-deriving status on the frontend from the last-seen lifecycle event.
  * Found and fixed a real contract drift: the previous local derivation treated `REQUEST_RECEIVED` as `"running"`, while the backend/state contract keeps a request `"pending"` until `EXECUTION_STARTED` — confirmed against the live API's actual `pending → running → completed` transitions.
  * Added `LiveExecutionStatus` + `isLiveExecutionStatus()` to `telemetry/liveTypes.ts`, matching the real `/status/:execution_id` response shape.
  * Updated `ExecutionMonitor.tsx` to surface the authoritative status, total duration (once terminal), execution error, and status-fetch errors — no visual redesign.
  * Verified via `tsc --noEmit` (0 errors) and a live smoke test against a running `services/api` instance: `POST /execute` → polled `GET /status/:id` through the full `pending → running → completed` transition with populated `end_time`, and verified the WebSocket `/stream/:id` events remain payload-less as documented.
  * Not wired into `DashboardLayout.tsx`/existing panels — out of scope for today (see `App.tsx`/`telemetry/README.md`).

### Current Status

* Gateway and orchestration foundation: **Integrated, Stabilized & Validated**
* Event schema and lifecycle: **Implemented & Validated**
* Execution state management: **Implemented & Validated**
* Provider abstraction & Tool execution: **Fully Compatible & Validated (38/38 tests passing)**
* EventStream → Watchdog dispatch seam: **Integrated & Validated**
* Watchdog live execution integration: **Connected & Validated**
* Pathway event-stream integration: **Deferred (Post-Core Stabilization)**
* REST/WebSocket Gateway integration: **Foundation Operational, State Contract Aligned — Real Integration Pending**
* Telemetry event representation & live consumption: **Implemented & Validated, Status Contract Aligned with `/status/:execution_id`**
* Dashboard UI integration: **Live Telemetry Monitor Implemented**
* End-to-end Gateway-Provider-Tool-Watchdog flow: **Verified & Operational**