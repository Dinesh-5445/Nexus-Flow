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

### Current Status

* Gateway and orchestration foundation: **Implemented & Validated**
* Event schema and lifecycle: **Implemented & Validated**
* Execution state management: **Implemented & Validated**
* Provider abstraction & Tool execution: **Compatible & Validated (28/28 tests passing)**
* EventStream → Watchdog dispatch seam: **Implemented & Validated**
* Pathway event-stream integration: **Pending (Day 3)**
* REST/WebSocket Gateway integration: **Pending (Day 3)**
* Telemetry event representation & mock consumption foundation: **Implemented & Validated (Harshit — Day 2)**
* Dashboard/telemetry integration (wiring into panels): **Pending**
* End-to-end system integration: **Pending (Day 3)**


