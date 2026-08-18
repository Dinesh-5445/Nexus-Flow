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
