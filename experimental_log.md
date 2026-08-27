# Experimental Log

This file records engineering experiments, architecture decisions, rejected approaches, benchmarks, design investigations, and engineering observations.

## Entries

### Date: 2026-08-15

**Experiment / Decision:**
Repository Architecture Restructuring

**Context:**
The initial repository structure organized directories around individual team members.

**Problem:**
A production-oriented repository should represent system architecture rather than developer ownership.

**Initial Approach:**
Developer-specific directories.

**Decision:**
Refactor the repository so physical directories represent system components:

* `src/`
* `services/`
* `frontend/`
* `tests/`
* `docs/`
* `logs/`
* `reference/`

**Ownership Mechanism:**
`CONTRIBUTION_GUIDE.md`

**Reason:**
Separate software architecture from team ownership while maintaining explicit ownership boundaries for collaborative Git development.

**Impact:**
The repository now represents the software architecture directly while ownership remains documented separately.

---

### Date: 2026-08-16

**Experiment / Decision:**
Gateway and Orchestrator Foundation Scaffolding

**Context:**
The first implementation day required establishing the physical boundaries for Gateway and Orchestration according to the ownership defined in `CONTRIBUTION_GUIDE.md`.

**Problem:**
The team needed to begin implementation without prematurely coupling the Gateway to the REST API, provider implementations, or Watchdog.

**Initial Approach:**
Keep `src/gateway/` and `src/orchestration/` as README-only placeholders.

**Decision:**
Created minimal Python module boundaries:

* `src/gateway/__init__.py`
* `src/gateway/router.py`
* `src/orchestration/__init__.py`
* `src/orchestration/executor.py`

The initial implementation was intentionally skeletal and used `TODO` markers rather than introducing concrete REST frameworks, provider implementations, or persistence mechanisms.

**Reason:**
Establish clear ownership and integration boundaries before defining the shared event and execution contracts.

**Impact:**
The Gateway and Orchestration layers now have explicit implementation boundaries for the subsequent event-driven execution flow.

---

### Date: 2026-08-16

**Experiment / Decision:**
API Service — REST/WebSocket Skeleton

**Context:**
`services/api` is the communication boundary between client applications and the Gateway.

**Problem:**
The team needed a running API foundation without prematurely finalizing Gateway integration or event schemas.

**Initial Approach:**
Review the Gateway and API architecture and establish the expected flow:

`Client / Dashboard → API → Gateway → Orchestration`

**Decision:**
Initialized `services/api` as a Node.js + TypeScript service using Express and `ws`.

Implemented:

* `GET /health` — working
* `POST /execute` — initial stub
* `GET /status/:execution_id` — initial stub
* WebSocket upgrade handling for `/stream/:execution_id`

Gateway forwarding, request validation, status lookup, and event emission were intentionally left for later integration.

**Reason:**
Provide Sayan with an independently runnable API boundary while allowing the Gateway and event contracts to stabilize independently.

**Impact:**
The API service can now serve as the integration boundary between external clients and the Python Gateway.

---

### Date: 2026-08-17

**Experiment / Decision:**
Provider Abstraction and Tool Execution Foundation

**Context:**
The provider and tool subsystems required stable interfaces that could be consumed by the Gateway and Orchestration layers without coupling orchestration logic to a specific LLM provider.

**Problem:**
The project needed provider and tool contracts for integration testing without introducing live vendor SDK dependencies or production routing complexity.

**Decision:**
Implemented a lightweight provider abstraction and asynchronous tool execution foundation.

**Provider Layer:**

* `BaseLLMProvider`
* `LLMMessage`
* `ToolCall`
* `LLMResponse`
* `ProviderConfig`
* `MockProvider`

**Tool Layer:**

* `BaseTool`
* `ToolRegistry`
* `ToolExecutor`
* `ToolResult`
* `CalculatorTool`
* `EchoTool`

`ToolResult.to_event_payload()` provides structured execution information compatible with downstream event consumers.

**Reason:**
Keep the provider/tool subsystem implementation-independent and allow the Gateway/Orchestrator to interact through stable interfaces.

**Scope Deliberately Deferred:**

* Live vendor SDK integration
* Dynamic provider routing
* Provider fallback
* Production tool routing
* Multi-agent execution
* Full Pathway streaming

**Validation:**
The provider and tool subsystem tests passed with 17 tests.

**Impact:**
The provider/tool subsystem provides a clean execution boundary for Gateway and Orchestration integration.

---

### Date: 2026-08-17

**Experiment / Decision:**
Gateway, Orchestration, and Event Contract Foundation — Day 2

**Context:**
The Gateway and Orchestration layers required a stable event-driven contract so that execution state and lifecycle information could be consumed by the API, Watchdog, and telemetry systems without coupling those systems to internal orchestration logic.

**Problem:**
The team needed an operational Gateway → Orchestrator → Provider/Tool execution path while avoiding premature introduction of distributed streaming, persistent state, or additional infrastructure.

**Decision:**

1. **Gateway lifecycle ownership**

   * Gateway owns request-level lifecycle events such as request receipt and final execution status.

2. **Orchestration lifecycle ownership**

   * Orchestrator owns execution-level and provider/tool execution events.

3. **Structured event contract**

   * Events use a common structured schema containing lifecycle information and execution metadata.
   * The event contract is intended to be consumed independently by the Watchdog, API layer, and telemetry components.

4. **Single-owner execution state**

   * Execution state is managed through a dedicated `StateManager`.
   * The Day 2 implementation uses in-memory state.

5. **Temporary event-stream implementation**

   * `EventStream` currently provides an in-memory event-stream abstraction.
   * It is treated as an integration boundary rather than the final streaming infrastructure.

6. **Pathway integration deferred**

   * Full Pathway-based streaming is intentionally deferred until the Gateway/Event contract is stable.
   * The Day 2 implementation therefore does not introduce Pathway-specific assumptions into the core orchestration interfaces.

**Implementation Result:**

The following execution path is operational:

`Gateway → Orchestrator → Mock Provider/Tool Execution → EventStream → StateManager`

Structured lifecycle events are emitted during execution, providing the initial contract for downstream consumers.

**Reason:**
Stabilize the execution and event contracts before introducing the full streaming implementation. This minimizes coupling and allows Koushik's Watchdog, Sayan's API layer, and Harshit's telemetry components to integrate against defined interfaces.

**Validation:**
The repository test suite passed with 19 tests.

**Deferred Work:**

* Full Pathway event-stream integration
* REST/WebSocket → Gateway integration
* Advanced execution-state persistence and recovery
* Expanded retry and multi-turn execution states

**Impact:**
The Day 2 implementation establishes the first operational Gateway/Orchestration execution path and provides the event and state contracts required for subsequent subsystem integration.

---

### Date: 2026-08-18

**Experiment / Decision:**
Day 2 Closure — EventStream → Watchdog Dispatch Seam

**Context:**
Following the compatibility audit, one remaining integration seam existed:
`EventStream` published events but had no mechanism to forward them to the `Watchdog`.

**Problem:**
`Watchdog.process_event()` expects a `Dict[str, Any]` payload (specifically with `event_type="tool_called"`).
`EventStream` stored full `Event` objects but did not dispatch them anywhere.
The seam `EventStream → Event.payload → Watchdog.process_event()` was unconnected.

**Decision:**
Added `EventStream.subscribe(callable)`. On every `publish()`, `event.payload` is forwarded to all registered subscribers after the event is stored. Callers connect `Watchdog.process_event` as a subscriber.

No new schema was introduced.
No event lifecycle values were renamed.
`src/events/schema.py` remains the sole authoritative event schema.
`Watchdog` remains a consumer; it does not own the schema.

**Implementation:**

* `src/events/stream.py` — added `subscribe()` and subscriber dispatch loop in `publish()`.
* `tests/test_eventstream_watchdog_integration.py` — 4 focused tests proving the contract.

**Day 2 Contracts (authoritative for teammates):**

| Contract | Detail |
|---|---|
| Authoritative event schema | `src/events/schema.py` — `Event`, `EventLifecycle` |
| EventStream | In-memory; full `Event` stored in `published_events` |
| Integration seam | `EventStream.subscribe(watchdog.process_event)` — subscribers receive `event.payload` |
| Gateway/Orchestrator | Own event production; publish via `EventStream.publish(Event(...))` |
| Watchdog (Koushik) | Consumes `Event.payload`; registered via `subscribe()` |
| Provider/Tool results (Jyothi) | `ToolResult.to_event_payload()` produces the payload Watchdog expects |
| API/REST (Sayan) | `event.to_dict()` provides stable JSON structure for transport |
| Telemetry (Harshit) | Can consume the event envelope/payload through `published_events` or subscriber registration |

**Validation:**
28 tests passed (24 pre-existing + 4 new integration tests).

**Intentionally Deferred to Day 3:**

* Full Pathway event-stream integration
* REST/WebSocket → Gateway integration (Sayan)
* Advanced execution-state persistence and recovery
* Expanded retry and multi-turn execution states
* Production anomaly types in Watchdog (Koushik)
* Live provider SDK integration (Jyothi)
* Telemetry pipeline (Harshit)

**Impact:**
Day 2 is complete. The `EventStream → Event.payload → Watchdog` integration seam is unambiguous and validated. All teammates can continue Day 3 work against stable, tested contracts without waiting for an architectural decision.

---


### Date: 2026-08-21

**Experiment / Decision:**
Watchdog Day 3 — Integration with Actual Execution Events

**Context:**
The Day 2 Watchdog prototype had been validated against Dinesh's event representation using sample/replayed events and an isolated stream integration test. Day 3 focused on connecting the Watchdog to events produced by the actual execution flow (`GatewayRouter` → `Orchestrator` → `ToolExecutor` → `ToolResult.to_event_payload()` → `EventStream`).

**Problem:**
The Watchdog needed to observe events generated during real execution flows rather than relying only on manually constructed or replayed events, while maintaining strict subsystem boundaries and avoiding changes to Dinesh's execution flow or shared event schema.

**Decision:**
Connected the existing Watchdog to the actual execution flow by registering `Watchdog.process_event` as an `EventStream` subscriber via `Watchdog.attach_to_event_stream(event_stream)`. Preserved the existing repeated-tool-call detection logic (`repeated_call_threshold=5`, `tool_history`, `Counter`).

**Implementation / Validation:**
- `src/watchdog/detector.py`: Added `self.alerts` list in `Watchdog.__init__` and `attach_to_event_stream(self, event_stream)` method to subscribe `process_event` to an `EventStream`.
- `tests/test_watchdog.py`: Added `TestWatchdogRealExecutionIntegration` containing 4 integration tests that trigger real execution flows via `GatewayRouter` / `Orchestrator` / `ToolExecutor` to verify:
  1. Real execution events reach Watchdog via `EventStream` (`test_real_execution_event_reaches_watchdog`).
  2. Normal tool execution below threshold does not generate an alert (`test_normal_execution_flow_no_alert`).
  3. Repeated tool calls during live gateway request execution trigger a `repeated_tool_call` alert upon hitting threshold (`test_repeated_tool_calls_in_real_execution_triggers_alert`).
  4. Tool calls across different requests maintain execution isolation (`test_request_execution_isolation_in_real_execution`).

**Testing:**
- Ran `python -m pytest tests/test_watchdog.py -v`: 9 passed (5 unit tests + 4 real execution integration tests).
- Ran full test suite `python -m pytest -v`: 32 passed (0 failures).

**Scope:**
- No timeout detection.
- No repeating workflow detection.
- No additional anomaly types.
- No anomaly scoring.
- No changes to Dinesh's shared event schema or Orchestrator logic.
- No unrelated architectural changes.

**Impact:**
The Watchdog is now connected to events produced by the actual execution flow and repeated-tool-call detection has been verified using live execution events without breaking any Day 1/Day 2 contracts.

=======
### Date: 2026-08-18

**Experiment / Decision:**
Day 2 Provider and Tool Compatibility Audit with Gateway Event Contract

**Context:**
On Day 2, the team established the first shared Gateway + Event contract and execution pipeline (`src/gateway/`, `src/orchestration/`, `src/events/`, `src/state/`). Jyothi's Day 2 responsibility is to inspect the shared contract, compare the existing Day 1 provider/tool implementation (`src/providers/`, `src/tools/`) against it, perform any necessary compatibility adjustments, ensure all tests pass, and document the findings without over-implementing.

**What was Inspected:**
* Dinesh's Gateway router and request/response models (`src/gateway/router.py`, `src/gateway/models.py`)
* Orchestrator execution flow (`src/orchestration/executor.py`)
* Event schema and EventStream abstraction (`src/events/schema.py`, `src/events/stream.py`)
* State management lifecycle (`src/state/manager.py`)
* Watchdog anomaly detector integration seam (`src/watchdog/detector.py`, `tests/test_eventstream_watchdog_integration.py`)
* Existing provider abstraction (`src/providers/base.py`, `src/providers/mock_provider.py`, `src/providers/__init__.py`)
* Existing tool execution engine (`src/tools/base.py`, `src/tools/builtin.py`, `src/tools/executor.py`, `src/tools/registry.py`, `src/tools/__init__.py`)
* Test suites across the entire repository (`tests/`)

**Dinesh's Discovered Event / Execution Contract:**
* **Gateway Request / Response Contract (`src/gateway/models.py`):**
  * `GatewayRequest`: `request_id: str`, `messages: List[Dict[str, Any]]`, `session_id: str = ""`, `parameters: Dict[str, Any]`.
  * `GatewayResponse`: `request_id: str`, `status: str`, `result: Optional[Any]`, `error: Optional[str]`, `execution_time_ms: float`.
* **Orchestrator Execution Contract (`src/orchestration/executor.py`):**
  * Invokes `self.provider.config.model_name` for `EXECUTION_STARTED` event emission.
  * Unpacks messages into `LLMMessage(**msg)`.
  * Retrieves tool schemas via `self.tool_executor.registry.get_schemas()`.
  * Calls `await self.provider.generate(messages=llm_messages, tools=tools_schema)`.
  * Checks `response.has_tool_calls` and iterates over `response.tool_calls`.
  * Executes each tool via `await self.tool_executor.execute_tool_call(tool_call, request_id=request.request_id, session_id=request.session_id)`.
  * Formats tool execution events via `tool_result.to_event_payload(request_id=request.request_id, session_id=request.session_id)` and publishes `Event(event_type=EventLifecycle.TOOL_EXECUTION, ...)`.
  * Formats final output containing `content` and `tool_results` (`tool_result.to_dict()`).
* **Event Schema Contract (`src/events/schema.py`):**
  * `EventLifecycle` enum: `REQUEST_RECEIVED`, `EXECUTION_STARTED`, `TOOL_EXECUTION`, `COMPLETED`, `FAILED`.
  * `Event` dataclass: `event_type: EventLifecycle`, `request_id: str`, `timestamp: float`, `payload: Dict[str, Any]`, `to_dict()`.
* **EventStream & Watchdog Seam (`src/events/stream.py`):**
  * `EventStream.publish(event)` stores `event` and synchronously dispatches `event.payload` to all registered subscribers (`subscribe(callable)`), directly connecting to `Watchdog.process_event(payload)`.

**Compatibility Analysis:**
1. **Provider Layer (`src/providers/`):**
   * `LLMMessage`: Fields (`role`, `content`, `name`, `tool_call_id`) and `to_dict()` perfectly match `Orchestrator`'s instantiation and message formatting.
   * `LLMResponse`: Attributes (`content`, `tool_calls`, `model`, `finish_reason`, `usage`, `raw_response`) and `@property has_tool_calls` match the exact access pattern in `Orchestrator.execute_flow`.
   * `ToolCall`: Standardized fields (`id`, `name`, `arguments`) match the arguments expected by `ToolExecutor.execute_tool_call`.
   * `ProviderConfig`: `model_name` and other configuration attributes are present and correctly read during execution.
   * `MockProvider`: Asynchronous `generate()` signature and deterministic mock responses fully integrate with `Orchestrator`.
2. **Tool Execution Layer (`src/tools/`):**
   * `ToolRegistry`: `get_schemas()` generates standard OpenAPI-compatible schemas consumed by the LLM provider; `get()`, `has()`, and `register()` operate as expected.
   * `ToolExecutor`: `execute_tool_call()` and `execute_many()` handle async execution, argument parsing, error containment, execution timing, and return `ToolResult`.
   * `ToolResult`:
     * `to_dict()` provides the structured dictionary format stored in orchestrator execution results.
     * `to_event_payload(request_id, session_id)` produces the exact payload dictionary (`event_type: "tool_called"`, `request_id`, `tool_name`, `status`, `session_id`, `tool_call_id`, `execution_time_ms`, `error`, `timestamp`) expected by `EventLifecycle.TOOL_EXECUTION` and consumed by Koushik's `Watchdog.process_event()`.

**Compatibility Changes Made:**
No provider/tool implementation changes were required. The Day 1 provider abstraction and tool execution interfaces were designed with high cohesion and clean boundaries, making them 100% compatible out-of-the-box with Dinesh's Day 2 Gateway/Event contract and Koushik's Watchdog.

**Files Changed:**
* `experimental_log.md` — Updated with Jyothi's Day 2 inspection, compatibility audit, and validation record.
* `logs/log.md` — Updated shared team log with verified Day 2 status.

**Tests Performed:**
* Ran full repository test suite (`python -m unittest discover -v -s tests`):
  * `test_providers.py`: 6 tests passed (unit tests for message serialization, response properties, env config, mock text/tool generation).
  * `test_tools.py`: 10 tests passed (unit tests for registry, schemas, calculator/echo execution, error handling, async concurrency, event payload formatting).
  * `test_provider_tools_flow.py`: 1 test passed (integration test verifying LLM request → MockProvider → ToolExecutor → ToolResult → Watchdog alert).
  * `test_gateway_orchestration.py`: 2 tests passed (Gateway → Orchestrator → Provider/Tool execution flow, state tracking, and lifecycle events).
  * `test_watchdog.py`: 5 tests passed (Watchdog anomaly detection unit tests).
  * `test_eventstream_watchdog_integration.py`: 4 tests passed (EventStream subscribe seam and payload dispatch to Watchdog).
  * **Total: 28 tests passing (0 failures, 0 errors, 0.144s).**

**Important Decisions & Deferred Scope:**
* Adhered strictly to the minimal compatibility rule: No unnecessary modifications were made just to generate code churn.
* Live provider integration (e.g. OpenAI, Anthropic, Gemini SDKs), dynamic routing, and production tool policies remain scheduled for future implementation stages.

**Final Status:**
Completed. The provider and tool subsystem is fully compatible with Dinesh's Gateway/Event contract, verified with 28 passing tests, and ready for Day 3 integration.



---

### Date: 2026-08-16

**Experiment / Decision:**
Frontend Dashboard Scaffold — Placeholder-Driven Foundation

**Context:**
No API contract (Sayan) or event schema (Dinesh) existed yet at Day 1. The
dashboard needed a starting structure that could be built and rendered
end-to-end without depending on either.

**Problem:**
Building against guessed data shapes risks locking in an incorrect contract
and violates the interface rule (don't invent APIs/event schemas before an
owner defines them).

**Initial Approach:**
Considered hardcoding a "best guess" event/session shape to move faster.

**Decision:**
Rejected the best-guess approach. Built the dashboard scaffold with
deliberately loose, optional-heavy types (`SessionInfo`, `ExecutionEvent`,
`Metrics`, `WatchdogAlert` in `types.ts`) fed entirely by local
`placeholderData.ts`, with every type file explicitly commented as
PLACEHOLDER / not-final-contract.

**Implementation:**
* `frontend/dashboard/src/App.tsx` — wires placeholder data into layout
* `frontend/dashboard/src/DashboardLayout.tsx`
* `frontend/dashboard/src/components/{SessionPanel,EventStreamPanel,MetricsPanel,AlertsPanel}.tsx`
* `frontend/dashboard/src/types.ts`
* `frontend/dashboard/src/data/placeholderData.ts`
* Vite + TypeScript + React project setup (`package.json`, `tsconfig.json`, `vite.config.ts`)

**Reason:**
Get a working, renderable dashboard shell in place without prematurely
coupling to contracts that Sayan and Dinesh hadn't finalized yet — keeps the
frontend independently developable per `CONTRIBUTION_GUIDE.md`.

**Deferred:**
* Real WebSocket/REST data
* Event schema-accurate types
* Watchdog alert format

**Impact:**
Dashboard renders end-to-end with placeholder data. Structure is in place to
receive real contracts once they exist, without requiring a rewrite of the
component tree.

---

### Date: 2026-08-18

**Experiment / Decision:**
Telemetry Event-Consumption Foundation — Mocked Event Source

**Context:**
Day 2 task (assigned scope): build the telemetry/event-consumption
foundation — not the full dashboard — and define how execution
events/status are represented for the frontend, using mocked events with no
dependency on the real execution pipeline.

**Problem:**
`services/api` (Sayan) has no working `/execute` or `/stream/:execution_id`
yet, so there's no real feed to connect to. At the same time, the existing
placeholder types in `types.ts` are intentionally loose and don't reflect
the real event contract Dinesh has since finalized (`src/events/schema.py`,
`src/gateway/router.py`, `src/orchestration/executor.py`,
`src/tools/base.py`, `src/state/manager.py`).

**Investigation:**
Read the actual backend event-producing code rather than guessing the
contract:
* `Event`/`EventLifecycle` envelope — `src/events/schema.py`
* `request_received`/`completed`/`failed` payloads — `src/gateway/router.py`
* `execution_started` payload — `src/orchestration/executor.py`
* `tool_execution` payload — `ToolResult.to_event_payload()` in `src/tools/base.py`
* execution status values (`pending`/`running`/`completed`/`failed`) — `src/state/manager.py`

**Finding (flagged, not resolved):**
`ToolResult.to_event_payload()` nests its own `request_id`, `timestamp`, and
a literal `event_type: "tool_called"` inside the `tool_execution` payload —
inconsistent with the outer envelope's `event_type`
(`EventLifecycle.TOOL_EXECUTION`). Reproduced exactly as-is rather than
silently normalized, and documented for Dinesh/Jyothi/Koushik.

**Decision:**
Created an isolated `frontend/dashboard/src/telemetry/` module:
* `types.ts` — schema-accurate `GatewayEvent` discriminated union + `ExecutionStatus`/`statusForEvent`
* `EventSource.ts` — transport-agnostic `subscribe`/`close` interface
* `mockEvents.ts` — generates a realistic mocked execution event sequence
* `MockEventSource.ts` — replays the mock sequence on a timer, implementing `EventSource`
* `useTelemetryEvents.ts` — React hook accumulating events + derived per-request status
* `index.ts`, `README.md`

Deliberately **not** wired into `App.tsx`/`DashboardLayout.tsx`/existing
panels or the existing `types.ts`/`placeholderData.ts` — that's dashboard
integration work, out of scope for the event-consumption foundation task.

**Reason:**
Keep event representation and consumption decoupled from transport so a
future `WebSocketEventSource` (once Sayan's `/stream/:execution_id` exists)
can implement the same interface and drop in with zero consumer changes.

**Validation:**
* `npx tsc --noEmit` on the dashboard project — 0 errors.
* Isolated Node smoke test of `mockEvents`/`MockEventSource`/`statusForEvent`
  — verified event ordering (`request_received → execution_started →
  tool_execution* → completed|failed`), payload shapes, the failure path, and
  `MockEventSource` replay order. All assertions passed.
* `npm run build` fails on a pre-existing scaffold gap (missing `index.html`)
  unrelated to this change — not something this task covers.

**Deferred:**
* Wiring `telemetry/` into `DashboardLayout`/panels and reconciling with
  existing `types.ts`/`placeholderData.ts`
* Real WebSocket source — depends on Sayan's `/stream/:execution_id`
* Resolving the `tool_called` vs `tool_execution` schema quirk — needs
  Dinesh/Jyothi/Koushik

**Impact:**
Frontend now has a schema-accurate, independently testable
event-consumption layer, ready to plug into the dashboard once panels move
off placeholder data — without depending on the still-stubbed real pipeline.


### Date: 2026-08-19

**Experiment / Decision:**
REST/WebSocket Gateway & Event Contract Alignment

**Context:**
Day 2 task (assigned scope): implement mock REST execution endpoints and WebSocket event streaming aligned with Dinesh's initial Gateway and event contracts, without requiring real Gateway backend integration yet.

**Problem:**
The existing `api/src/index.ts` skeleton contained stubbed `/execute` and `/status` endpoints, lacked type definitions for Gateway/Event contracts, and had no WebSocket client connection tracking or event dispatch logic. Front-end telemetry development (Harshit) was blocked on having a functional `/stream/:execution_id` endpoint to connect against.

**Investigation:**
Reviewed Dinesh's Gateway request/response standard dataclasses and Event schema definitions:
* `EventLifecycle` state progression (`request_received` → `execution_started` → `tool_execution` → `completed` | `failed`).
* `ExecutionEvent` timestamp requirements — Unix floating-point seconds matching Python's `time.time()`, necessitating `Date.now() / 1000` in TypeScript.
* Connection routing constraints for streaming events to specific execution listeners.

**Decision:**
Implemented the REST and WebSocket Gateway layer in `api/`:
* `types.ts` — schema-accurate TypeScript interfaces for `GatewayRequest`, `GatewayResponse`, `ExecutionEvent`, and `EventLifecycle`.
* `POST /execute` — added payload validation (`request_id`, `messages`), initial state tracking, `202 Accepted` response with `stream_url`, and triggered async mock execution.
* `GET /status/:execution_id` — added polling fallback using an in-memory `executionStatus` map with `404` handling for invalid execution IDs.
* WebSocket Handler — configured route matching for `/stream/:execution_id` with per-request client pooling using a `streamClients` map (`Map<string, Set<WsWebSocket>>`) and auto-cleanup on client socket `close`.
* `emitEvent` & `simulateExecution` — built event broadcasting logic and a step simulator emitting mock lifecycle events at 500ms intervals.

**Reason:**
Isolate and standardise the API transport layer so clients can consume real-time WebSocket events and REST endpoints matching the finalized contract immediately, decoupling frontend stream development from backend execution engine readiness.

**Validation:**
* `npx tsc --noEmit` — 0 TypeScript compiler errors.
* `curl` testing for `POST /execute` (verified `202 Accepted` and `stream_url`) and `GET /status/:execution_id` (verified state updates from `request_received` to `completed`).
* Live WebSocket streaming verified via `wscat` / Postman connecting to `ws://localhost:3000/stream/:execution_id` — confirmed correctly ordered JSON event delivery and clean disconnect handling.

**Deferred:**
* Replacing `simulateExecution` with real Gateway / Orchestrator integration.
* Wiring Pathway event-stream pipeline into the REST/WebSocket layer (Day 3).

**Impact:**
REST/WebSocket Gateway now strictly matches the team's event contract, providing a fully functional streaming interface that unblocks frontend dashboard telemetry integration.

---

### Date: 2026-08-20

**Experiment / Decision:**
Day 3 — Provider/Tool Integration Verification and Gateway Execution Boundary

**Context:**
Day 3 connected the Gateway/Orchestrator execution path with the existing provider/tool subsystem while keeping subsystem ownership and service boundaries intact.

**What was verified:**
* Gateway request handling and Orchestrator execution flow.
* `BaseLLMProvider`, `MockProvider`, `LLMMessage`, `LLMResponse`, and `ToolCall` compatibility with the Orchestrator.
* `ToolRegistry`, `ToolExecutor`, and `ToolResult` integration.
* `ToolResult.to_event_payload()` → `Event(EventLifecycle.TOOL_EXECUTION)` → `EventStream` → `Watchdog.process_event()` mapping.
* State transitions and lifecycle events: `REQUEST_RECEIVED → EXECUTION_STARTED → TOOL_EXECUTION → COMPLETED/FAILED`.

**Execution Flow:**
`Gateway → Orchestrator → Provider → ToolExecutor → ToolResult → EventStream → Watchdog → Gateway response`

The provider and tool interfaces matched the existing Orchestrator contracts. No provider/tool implementation changes were required.

**Gateway/API Boundary Decision:**
The Python Gateway/Orchestration path remains independent of the Node.js API service. API-specific child-process/stdout handling was not kept inside the Python execution layer. `src/main.py` remains a Python execution entry point that wires the Python subsystems, while cross-service communication is deferred to an agreed integration mechanism in a later phase.

**Coordination Finding:**
The outer event uses `EventLifecycle.TOOL_EXECUTION`, while the payload contains `event_type: "tool_called"` for the existing Watchdog subscriber contract. This was verified as intentional and was not changed.

**Validation:**
Full repository test suite passed:

`python -m unittest discover -v -s tests`

**Result:** 28/28 tests passed, with 0 failures and 0 errors.

**Deferred:**
* Live OpenAI/Anthropic/Gemini provider SDK integration.
* Production provider routing/fallback and expanded tool policies.
* REST/WebSocket → Gateway integration.
* Full Pathway streaming and advanced execution-state persistence/recovery.

**Files Changed:**
* `experimental_log.md` — Day 3 verification and architectural decision record.
* `logs/log.md` — shared Day 3 status.

**Final Status:**
Day 3 provider/tool integration verification is complete. The existing Provider/Tool subsystem is compatible with the Gateway/Orchestration execution path, and the Python execution boundary remains decoupled from the Node.js API layer. Ready for Day 4.

---

### Date: 2026-08-27

**Experiment / Decision:**
Day 4 Provider and Tool Foundation Verification

**Context:**
Day 4 task (assigned scope): Verify the existing provider and tool execution implementations against Dinesh's stabilized Gateway → Orchestrator execution flow. Validate the three required execution cases: Success Case (normal provider response), Tool Execution Case (tool call generation, execution, and event emission), and Failure Cases (runtime error containment, unavailable tools, invalid arguments, and provider exception propagation). Ensure provider/tool results continue to map cleanly to the shared event/state contracts without introducing premature features or architectural churn.

**What was Inspected:**
* Gateway router and request/response models (`src/gateway/router.py`, `src/gateway/models.py`)
* Orchestrator execution engine (`src/orchestration/executor.py`)
* Event schema and EventStream pub/sub dispatch (`src/events/schema.py`, `src/events/stream.py`)
* Execution state manager (`src/state/manager.py`)
* Main Python execution entry point (`src/main.py`)
* Provider abstraction layer (`src/providers/base.py`, `src/providers/mock_provider.py`)
* Tool execution subsystem (`src/tools/base.py`, `src/tools/registry.py`, `src/tools/executor.py`, `src/tools/builtin.py`)
* Watchdog anomaly detection subsystem (`src/watchdog/detector.py`)
* All unit and integration test suites (`tests/`)

**Current Gateway/Orchestrator Integration Flow:**
1. **Gateway Ingestion:** `GatewayRouter.handle_request(request: GatewayRequest)` creates an `ExecutionState(status="pending")` via `StateManager` and publishes `EventLifecycle.REQUEST_RECEIVED`.
2. **Execution Initialization:** Updates state to `"running"` and invokes `await Orchestrator.execute_flow(request)`.
3. **Orchestrator Step:** Emits `EventLifecycle.EXECUTION_STARTED` with `payload={"provider_model": self.provider.config.model_name}`.
4. **Provider Invocation:** Unpacks `request.messages` into `[LLMMessage(**msg)]`, retrieves tool schemas from `self.tool_executor.registry.get_schemas()`, and calls `await self.provider.generate(messages=llm_messages, tools=tools_schema)`.
5. **Tool Execution:** If `response.has_tool_calls`, iterates through `response.tool_calls`, invoking `await self.tool_executor.execute_tool_call(tool_call, request_id=..., session_id=...)`. Emits `EventLifecycle.TOOL_EXECUTION` with payload generated by `tool_result.to_event_payload()` and records `tool_result.to_dict()` into `final_result["tool_results"]`.
6. **Completion / Failure:** Gateway updates state to `"completed"` / `"failed"` and emits `EventLifecycle.COMPLETED` or `EventLifecycle.FAILED`.

**Provider Compatibility Findings:**
* `BaseLLMProvider`: `config.model_name` and `generate(messages, tools, **kwargs)` match Orchestrator's invocation pattern.
* `LLMMessage`: Field mapping (`role`, `content`, `name`, `tool_call_id`) and unpacking match request messages.
* `LLMResponse`: Attributes (`content`, `tool_calls`, `model`, `finish_reason`, `usage`) and `@property has_tool_calls` match Orchestrator's conditional tool loop.
* `MockProvider`: Asynchronous response generation, tool call triggering on keyword `"calculate"`, and predefined response queue support all required integration patterns.
* **Result:** No provider implementation changes were required.

**Tool Compatibility Findings:**
* `ToolRegistry`: Tool registration (`register`), lookup (`get`, `has`), and OpenAPI schema export (`get_schemas`) operate as expected.
* `ToolExecutor`: Handles asynchronous invocation, stringified or dict JSON argument parsing, execution timing (`time.perf_counter()`), error containment (`TypeError`, `Exception`), and concurrent execution (`execute_many`).
* `ToolResult`: `to_dict()` produces clean dictionary representation for Orchestrator return value, and `to_event_payload()` accurately formats `EventLifecycle.TOOL_EXECUTION` payloads consumed by EventStream and Watchdog subscribers.
* `CalculatorTool` & `EchoTool`: Provide deterministic arithmetic evaluation and parameter echo prototypes.
* **Result:** No tool implementation changes were required.

**Validation of Required Test Cases (`tests/test_provider_tools_flow.py`):**
1. **A. Success Case (`test_provider_success_flow_without_tools`):**
   * Verified standard conversation prompt ("Explain NexusFlow architecture") -> Provider returns text -> Orchestrator constructs `{"content": "...", "tool_results": []}` -> State marked `completed`.
2. **B. Tool Execution Case (`test_provider_tool_execution_flow_via_orchestrator`, `test_complete_provider_tool_watchdog_flow`):**
   * Verified user math prompt -> Provider returns `ToolCall(calculator, 10 + 20)` -> ToolExecutor evaluates expression -> `ToolResult(status="completed", result={"expression": "10 + 20", "result": 30})` -> Orchestrator appends result and publishes `TOOL_EXECUTION` event.
3. **C. Failure Cases:**
   * **C1. Tool Execution Error (`test_provider_tool_execution_failure_handling`):** Arithmetic error (division by zero) is safely caught by `ToolExecutor` and returned as `ToolResult(status="failed", error="Tool execution failed: ...")`. Orchestrator completes without crashing, emitting `TOOL_EXECUTION` with failure payload.
   * **C2. Unavailable Tool (`test_provider_unavailable_tool_failure_handling`):** Request for unregistered tool returns `ToolResult(status="failed", error="Tool '...' is not registered.")`.
   * **C3. Invalid Arguments (`test_provider_invalid_arguments_failure_handling`):** Passing invalid argument names triggers `TypeError` containment in `ToolExecutor` returning `ToolResult(status="failed", error="Invalid tool arguments: ...")`.
   * **C4. Provider Exception Propagation (`test_provider_exception_propagation`):** Unhandled provider exceptions (e.g. connection timeout) cleanly propagate to the Orchestrator/Gateway layer to allow proper error handling and state transition to `failed`.

**Event / State Mapping Verification:**
* Verified that provider model name is emitted in `EXECUTION_STARTED`.
* Verified that `ToolResult.to_event_payload()` matches `EventLifecycle.TOOL_EXECUTION` and includes `request_id`, `tool_name`, `status`, `session_id`, `tool_call_id`, `execution_time_ms`, `error`, and `timestamp`.
* Verified that tool results in the Gateway response match the agreed dictionary format.

**Files Changed:**
* `tests/test_provider_tools_flow.py` — Added comprehensive tests covering the success case, tool execution case, and all failure paths.
* `experimental_log.md` — Updated with Jyothi's Day 4 verification record and findings.
* `logs/log.md` — Updated shared team log with verified Day 4 progress across all subsystems.

**Tests Performed:**
* Full test suite: `python -m unittest discover -v -s tests` -> 38/38 tests passing (0 failures, 0 errors, 0.196s).
* Module test execution: `python -m unittest tests/test_providers.py tests/test_tools.py tests/test_provider_tools_flow.py -v` -> 23 tests passing.
* Python main entry point smoke test: `python -m src.main` verified via JSON stdin for both text and tool requests.

**Scope Deliberately Deferred:**
* Live provider SDK integrations (OpenAI, Anthropic, Gemini).
* Dynamic provider routing / fallbacks.
* Advanced tool authorization policies and persistent registries.
* Pathway streaming infrastructure.

**Final Status:**
Completed. The Provider and Tool subsystem foundation is fully verified, 100% compatible with Dinesh's Gateway/Orchestrator flow, passes all 38 test cases, and is clean and ready for Day 5.

---

### Date: 2026-08-27

**Experiment / Decision:**
Watchdog Day 4 — Execution Event Integration and Request Isolation Verification

**Context:**
The Watchdog had previously been adapted to the shared execution/event representation. The current repository baseline includes the stabilized Gateway → Orchestrator → Provider/Tool execution flow (`GatewayRouter` → `Orchestrator` → `ToolExecutor` → `ToolResult.to_event_payload()` → `EventStream`) and subscriber integration.

**Objective:**
Verify that the Watchdog observes events produced by the actual execution flow and that the existing repeated-tool-call detection correctly handles repeated calls while maintaining request isolation.

**Verification:**
- Verified Watchdog observation of events produced by the actual execution flow (`GatewayRouter` → `Orchestrator` → `ToolExecutor` → `ToolResult.to_event_payload()` → `EventStream` → `Watchdog.process_event()`).
- Verified `EventStream` → `Watchdog` event delivery via `Watchdog.attach_to_event_stream(event_stream)` subscriber registration.
- Verified repeated-tool-call detection using execution-flow events (5 repeated tool calls trigger `repeated_tool_call` alert at threshold = 5).
- Verified request-based isolation of Watchdog tool history (`self.tool_history` dictionary keyed by `request_id`).
- Verified compatibility with the current `EventLifecycle.TOOL_EXECUTION` (`"tool_execution"`) event representation.

**Implementation / Changes:**
No new production Watchdog code was required. The existing Watchdog implementation in `src/watchdog/detector.py` and real execution integration tests in `tests/test_watchdog.py` were verified against the updated Gateway/Orchestration execution baseline. No new anomaly types or detection logic were introduced.

**Testing:**
- `python -m pytest tests/test_watchdog.py -v` — 9 passed in 0.10s (5 unit tests + 4 real execution integration tests)
- `python -m pytest tests/test_eventstream_watchdog_integration.py -v` — 4 passed in 0.05s
- `python -m pytest -v` — 38 passed in 0.43s (full repository test suite)

**Scope:**
- Repeated-tool detection: verified.
- Request isolation: verified.
- Actual execution event integration: verified.
- Timeout detection: not added.
- Repeating workflow detection: not added.
- Additional anomaly types: not added.
- Anomaly scoring: not added.
- Shared event schema redesign: not performed.
- Unrelated architectural changes: not performed.

**Impact:**
The Watchdog has been verified against the current execution/event flow and observes relevant execution events while preserving the existing repeated-tool-call detection and request isolation behavior.

