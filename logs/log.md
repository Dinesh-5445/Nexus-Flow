# Engineering Log

This file records the chronological implementation and development progress of the NexusFlow project.
*Note: See `experimental_log.md` for technical decisions, architectural experiments, and integration observations.*

## Day 1: 2026-08-16 — Repository & Architecture Foundation

* **Dinesh (Gateway / Orchestration):**
  * Established initial repository structure across `src/`, `services/`, `frontend/`, `tests/`, `docs/`, `logs/`, and `reference/`.
  * Implemented `src/gateway/router.py` with the initial `GatewayRouter.handle_request()` skeleton.
  * Implemented `src/orchestration/executor.py` with the initial `Orchestrator.execute_flow()` skeleton.
  * Established the initial Gateway → Orchestrator execution structure.
  * *Status*: Pathway, event, and state modules remained as initial structures pending Day 2 implementation.

* **Jyothi (LLM / Provider / Tool Execution):**
  * Implemented the provider abstraction layer (`src/providers/base.py`, `src/providers/mock_provider.py`).
  * Added `BaseLLMProvider`, `LLMMessage`, `LLMResponse`, `ToolCall`, and `ProviderConfig`.
  * Implemented the tool execution engine (`src/tools/base.py`, `src/tools/registry.py`, `src/tools/executor.py`, `src/tools/builtin.py`).
  * Added `BaseTool`, `ToolRegistry`, `ToolExecutor`, `ToolResult`, `CalculatorTool`, and `EchoTool`.
  * Added Watchdog-compatible event formatting through `ToolResult.to_event_payload()`.
  * Added provider and tool tests.
  * *Status*: Foundation complete.

* **Koushik (Watchdog / Anomaly Detection):**
  * Implemented the initial `Watchdog` prototype in `src/watchdog/detector.py`.
  * Added repeated tool-call detection with an initial threshold of 5 calls.
  * Documented initial monitoring signals in `docs/watchdog/monitoring-signals.md`.
  * *Status*: Foundation merged.

* **Sayan (REST / WebSocket API):**
  * Initialized the Node.js + TypeScript API service under `services/api`.
  * Added Express and WebSocket (`ws`) infrastructure.
  * Implemented initial `/health`, `/execute`, `/status/:execution_id`, and WebSocket `/stream/:execution_id` endpoints.
  * *Status*: Endpoints `/execute` and `/status/:execution_id` remain integration stubs pending Gateway integration.

* **Harshit (Frontend / Dashboard / Telemetry):**
  * Scaffolded the dashboard as a Vite + React + TypeScript project under `frontend/dashboard/`.
  * Implemented `App.tsx`, `DashboardLayout.tsx`, and four panel components (`SessionPanel`, `EventStreamPanel`, `MetricsPanel`, `AlertsPanel`).
  * Defined intentionally loose placeholder types and local `placeholderData.ts`, since no API contract existed yet.
  * *Status*: UI scaffolded, chat client unstarted.

## Day 2: 2026-08-17 & 2026-08-18 — Gateway, Event Contract & Subsystem Compatibility

* **Dinesh (Gateway / Orchestration):**
  * Established the first stable Gateway/Event integration contract and lifecycle definitions (`src/events/schema.py`).
  * Implemented in-memory `EventStream` with `subscribe()` payload dispatch seam (`src/events/stream.py`).
  * Implemented execution state management via `StateManager` (`src/state/manager.py`).
  * Added `GatewayRequest` and `GatewayResponse` models (`src/gateway/models.py`) and `GatewayRouter` (`src/gateway/router.py`).
  * Implemented the Gateway → Orchestrator → Provider/Tool execution flow (`src/orchestration/executor.py`).
  * Added integration tests (`tests/test_gateway_orchestration.py`, `tests/test_eventstream_watchdog_integration.py`).
  * *Status*: Contracts stabilized.

* **Jyothi (LLM / Provider / Tool Execution):**
  * Performed compatibility audit of provider and tool subsystems against Dinesh's Gateway/Event contract.
  * Verified full compatibility of `BaseLLMProvider`, `MockProvider`, `ToolExecutor`, `ToolRegistry`, and `ToolResult.to_event_payload()`.
  * Validated full test suite with 28/28 tests passing.
  * *Status*: Zero provider/tool code modifications required. Fully compatible.

* **Koushik (Watchdog / Anomaly Detection):**
  * Verified Watchdog prototype integration with `EventStream` via the subscriber dispatch seam.
  * Confirmed reception of `tool_called` payloads produced by `ToolResult.to_event_payload()`.
  * Validated repeated tool-call anomaly detection across unit and integration tests.
  * *Status*: Event stream integration verified.

* **Sayan (REST / WebSocket API):**
  * Maintained API foundation. Added `api/src/types.ts` representation of Gateway contracts.
  * Implemented `POST /execute`, `GET /status/:execution_id`, and `simulateExecution` (mock step execution engine emitting events every 500ms).
  * Implemented WebSocket upgrade handler for `/stream/:execution_id`.
  * Verified via Postman and `wscat`.
  * *Status*: Mock pipeline operational, Python Gateway integration pending.

* **Harshit (Frontend / Dashboard / Telemetry):**
  * Added `frontend/dashboard/src/telemetry/` modeled directly on the finalized Gateway contract.
  * Implemented `EventSource`, `MockEventSource`, and `useTelemetryEvents` React consumption hook.
  * Flagged an existing contract inconsistency in `ToolResult.to_event_payload()` (`event_type: "tool_called"` conflicting with `EventLifecycle.TOOL_EXECUTION`).
  * *Status*: Verified isolated smoke tests. Pending Sayan's `/stream/:execution_id` for UI wiring.

## Day 3: 2026-08-20 — Provider/Tool & Gateway Orchestration Integration

* **Dinesh (Gateway / Orchestration):**
  * Connected Gateway core and Orchestrator to the provider abstraction layer and tool execution engine in `src/main.py`.
  * Replaced mock execution point with real Provider and Tool Executor paths.
  * Verified lifecycle event emission (`REQUEST_RECEIVED` → `EXECUTION_STARTED` → `TOOL_EXECUTION` → `COMPLETED`/`FAILED`).
  * Resolved the `tool_called` vs `tool_execution` contract inconsistency.
  * *Status*: Pathway event-stream integration deferred to prioritize core stability.

* **Jyothi (LLM / Provider / Tool Execution):**
  * Verified end-to-end integration of provider abstraction and tool execution subsystem with the Orchestrator flow.
  * Verified message normalization, OpenAPI schema generation, and tool execution formatting.
  * *Status*: Full test suite passing (28/28 tests).

* **Koushik (Watchdog / Anomaly Detection):**
  * Verified Watchdog integration receiving events emitted during live execution via `EventStream.publish()`.
  * Validated repeated tool-call anomaly detection on live events.
  * *Status*: Live execution anomaly detection verified.

* **Sayan & Harshit (API & Frontend):**
  * Maintained respective subsystems, holding stable while waiting for the live Python pipeline to be connected to the API layer.

## Day 4: 2026-08-27 & 2026-08-28 — Foundation Stabilization & Subsystem Verification

* **Dinesh (Gateway / Orchestration):**
  * Verified Gateway → Orchestrator → Provider/Tool execution flow using existing interfaces.
  * Stabilized Gateway/Event/State contracts and execution output.
  * Isolated `tests/test_provider_tools_flow.py` from external dependencies.

* **Jyothi (LLM / Provider / Tool Execution):**
  * Verified provider and tool subsystems against stabilized flow.
  * Validated 3 execution scenarios: Success (text-only), Tool execution, and Failure cases (arithmetic runtime errors, unregistered tools, invalid arguments, provider exceptions).
  * Expanded `tests/test_provider_tools_flow.py` with comprehensive integration tests.
  * *Status*: Full test suite passing (38/38 tests).

* **Koushik (Watchdog / Anomaly Detection):**
  * Connected Watchdog to live execution events via `attach_to_event_stream()`.
  * Validated live event processing, repeated tool call alert generation, and request isolation via `tests/test_watchdog.py`.

* **Sayan (REST / WebSocket API):**
  * Verified `GatewayRequest`/`GatewayResponse`/`Event` alignment with Day 2 schema.
  * Updated `/execute` and `/status/:execution_id` to track `start_time`/`end_time`/`status` consistent with `ExecutionState`.
  * Mapped internal lifecycle events to real states (`pending`/`running`/`completed`/`failed`).

* **Harshit (Frontend / Dashboard / Telemetry):**
  * Implemented live telemetry execution monitoring (`ExecutionMonitor.tsx`).
  * Finalized live execution-status representation, pulling from `/status/:execution_id` to match the backend contract (`pending` -> `running` -> `completed`).

## Day 5: 2026-08-29 — V1 Integration & Stabilization

* **Dinesh (Gateway / Orchestration):**
  * Stabilized Gateway → Orchestrator → Provider/Tool execution flow.
  * Added `LLM_EXECUTION` event to `EventLifecycle` to complete ordering: `REQUEST_RECEIVED` → `EXECUTION_STARTED` → `LLM_EXECUTION` / `TOOL_EXECUTION` → `COMPLETED`.
  * Verified failure path (`REQUEST_RECEIVED` → `EXECUTION_STARTED` → `FAILED`).
  * *Status*: Adding `LLM_EXECUTION` caused tests in `tests/test_provider_tools_flow.py` (owned by Jyothi) to fail due to hardcoded event sequence assertions. Left unmodified to respect subsystem boundaries.

## Day 6: 2026-08-31 — Gateway/Orchestration Hardening & Verification

* **Dinesh (Gateway / Orchestration):**
  * Hardened the GatewayRouter → Orchestrator → Provider/Tool execution pipeline.
  * Added extensive integration tests in `tests/test_gateway_orchestration.py` to cover:
    * Successful full request executions.
    * Tool execution failures (e.g., `ValueError` inside a tool).
    * Provider failures (e.g., mocked API downtime).
    * Invalid request format edge cases.
  * Verified that exception handling in the Orchestrator successfully traps errors, emits a `FAILED` event, updates the StateManager to `failed`, and does not crash the Python process.
  * Restructured `MockProvider` tests to correctly clear queue state between test runs, fixing test isolation.
  * *Status*: Gateway tests are fully green (4/4 passed). Gateway pipeline hardened without API layer dependencies.

* **Jyothi (LLM / Provider / Tool Execution):**
  * Maintained provider/tool interfaces. Subsystem verified as highly stable.

* **Koushik (Watchdog / Anomaly Detection):**
  * Watchdog verified and operating as expected based on payload subscriptions.

* **Sayan (REST / WebSocket API):**
  * Temporarily unavailable. Work is blocked/pending for live Python integration with the API boundaries.

* **Harshit (Frontend / Dashboard / Telemetry):**
  * Blocked by API dependency. Awaiting Sayan's live Python pipeline integration to wire real telemetry to the UI panels.

---

## Current System State

* **Gateway and Orchestration**: Integrated, Stabilized, Hardened, and Verified natively in Python (Dinesh).
* **Event Schema and Lifecycle**: Implemented and Validated. Lifecycle strictly follows `REQUEST_RECEIVED` -> `EXECUTION_STARTED` -> `LLM_EXECUTION` -> (`TOOL_EXECUTION`...) -> `COMPLETED`/`FAILED`.
* **Execution State Management**: Implemented and Validated (`pending` -> `running` -> `completed`/`failed`).
* **Provider Abstraction & Tool Execution**: Fully Compatible and Integrated natively (Jyothi).
* **EventStream & Watchdog**: Dispatch seam active; Watchdog live execution detection connected and validated (Koushik).
* **REST/WebSocket API**: State contracts aligned with Python logic, but live Python Gateway integration is still pending (Sayan).
* **Telemetry & Dashboard**: Frontend representation implemented and aligned with `/status` contracts, pending live websocket data (Harshit).
* **Pathway Event-Stream Integration**: Intentionally Deferred (post-core stabilization).

## Pending / Blocked / Deferred Work

* **Sayan**: Needs to replace the simulated Node.js execution engine with a bridge to the live Python Gateway/Orchestrator pipeline.
* **Harshit**: Blocked waiting on the API integration (Sayan) to finalize dashboard WebSocket wiring.
* **Jyothi**: Needs to update `tests/test_provider_tools_flow.py` to account for the new `LLM_EXECUTION` event added on Day 5, or switch to asserting on event presence rather than hardcoded sequence lengths.
* **Dinesh**: Pathway integration deferred.