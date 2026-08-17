<<<<<<< Updated upstream
# Experimental Log

This file records engineering experiments, architecture decisions, rejected approaches, benchmarks, design investigations, and engineering observations.

## Entries

### Date: 2026-08-15
**Experiment / Decision:**
Repository Architecture Restructuring

**Context:**
The initial repository structure organized directories by individual team members.

**Problem:**
A production-style GitHub repository should represent software architecture rather than developer ownership.

**Initial approach:**
Developer-specific directories.

**Decision:**
Refactor the repository so physical directories represent system components.

**New architectural organization:**
- `src/`
- `services/`
- `frontend/`
- `tests/`
- `docs/`
- `logs/`
- `reference/`

**Ownership mechanism:**
`CONTRIBUTION_GUIDE.md`

**Reason:**
Separate software architecture from team ownership and make the repository suitable for collaborative Git-based development.

**Impact:**
The repository now looks like a coherent solo-developed software project while maintaining explicit team ownership documentation.

### Date: 2026-08-16
**Experiment / Decision:**
Gateway and Orchestrator Foundation Scaffolding

**Context:**
First coding day. Needed to establish where Gateway and Orchestration logic will live based on ownership defined in `CONTRIBUTION_GUIDE.md`. 

**Problem:**
Need to start coding without premature architectural decisions, keeping things minimal and decoupled from other modules.

**Initial approach:**
Empty README placeholders in `src/gateway/` and `src/orchestration/`.

**Decision:**
Created minimal Python modules with placeholder logic:
- `src/gateway/__init__.py` & `src/gateway/router.py` for routing.
- `src/orchestration/__init__.py` & `src/orchestration/executor.py` for single-agent orchestration.
Used `TODO`s instead of hardcoding architectures like REST frameworks or Provider layers.

**Reason:**
Prevents tight coupling on Day 1. Gives clear, structural boundaries for the Web/API platform to call into the Gateway, and for Provider/Watchdog components to hook into the Orchestrator.

**Impact:**
A starting foundation is in place. Next steps involve defining the Event Schema and API Contracts.\n
=======
# Experimental Log

This file records engineering experiments, architecture decisions, rejected approaches, benchmarks, design investigations, and engineering observations.

## Entries

### Date: 2026-08-15
**Experiment / Decision:**
Repository Architecture Restructuring

**Context:**
The initial repository structure organized directories by individual team members.

**Problem:**
A production-style GitHub repository should represent software architecture rather than developer ownership.

**Initial approach:**
Developer-specific directories.

**Decision:**
Refactor the repository so physical directories represent system components.

**New architectural organization:**
- `src/`
- `services/`
- `frontend/`
- `tests/`
- `docs/`
- `logs/`
- `reference/`

**Ownership mechanism:**
`CONTRIBUTION_GUIDE.md`

**Reason:**
Separate software architecture from team ownership and make the repository suitable for collaborative Git-based development.

**Impact:**
The repository now looks like a coherent solo-developed software project while maintaining explicit team ownership documentation.\n


### Date: 2026-08-16
**Experiment / Decision:**
API Service — REST/WebSocket Skeleton

**Context:**
`services/api` is the primary REST and WebSocket interface between the client/dashboard and the Gateway. Before today it contained only a README.

**Problem:**
The team needed a minimal, running foundation for the API layer — validated against the Gateway's expected request shape and the planned WebSocket event flow — without finalizing schemas or building real Gateway integration yet.

**Initial approach:**
Reviewed the API and Gateway READMEs to map the request flow (Client/Dashboard → API → Gateway → Orchestration)

**Decision:**
Initialized `services/api` as a Node.js + TypeScript project (Express + `ws`). Built a minimal skeleton:
- `GET /health` — working
- `POST /execute` — stubbed (TODO: validation, Gateway forwarding)
- `GET /status/:execution_id` — stubbed (TODO: status lookup)
- WebSocket upgrade handling on `/stream/:execution_id` — connects and logs, no event emission yet

No Gateway integration or schema finalization done yet, per agreement — foundation only.

**Impact:**
`services/api` now boots and exposes the interface shape the rest of the team can build against.


### Date: 2026-08-17
**Experiment / Decision:**
Provider Abstraction Layer & Tool Execution Engine — Day 1 Foundation Prototype & Scope Audit

**Context:**
`src/providers/` and `src/tools/` define the core AI subsystem owned by Jyothi Kiran. Prior to Day 1, both directories contained only README documentation files.

**Problem:**
Establish the minimal Day 1 foundation prototype for LLM provider abstraction and tool execution without premature over-engineering or implementing future-day scope. The goal is to define the necessary interfaces and understand the basic flows:
- `LLM request → provider → response`
- `Tool request → tool execution → result`

**Files Inspected:**
- `README.md`, `CONTRIBUTION_GUIDE.md`, `docs/architecture/README.md`, `docs/integration/README.md`
- `src/gateway/router.py`, `src/orchestration/executor.py`, `src/watchdog/detector.py`, `docs/watchdog/monitoring-signals.md`
- `services/api/src/index.ts`

**Initial approach vs. Decision:**
Avoided pulling in heavy external vendor SDKs (e.g. live OpenAI/Anthropic/Gemini SDKs), multi-agent routing, or complex persistence layers on Day 1. Instead, built a clean, decoupled foundation using Python's standard library and asyncio:
1. **Provider Abstraction (`src/providers/base.py`, `src/providers/mock_provider.py`):**
   - `BaseLLMProvider`: Abstract base class defining `async def generate(messages, tools, **kwargs) -> LLMResponse`.
   - `LLMMessage`, `ToolCall`, `LLMResponse`: Normalized dataclass contracts for messages, tool requests, and model responses.
   - `ProviderConfig`: Environment-based configuration loader to prevent hardcoded secrets.
   - `MockProvider`: Deterministic mock provider supporting predefined responses and predictable tool calling for offline testing.
2. **Tool Execution Engine (`src/tools/base.py`, `src/tools/registry.py`, `src/tools/executor.py`, `src/tools/builtin.py`):**
   - `BaseTool`: Abstract base class with JSON schema generator (`to_schema()`) and `async def execute(**kwargs)`.
   - `ToolRegistry`: Simple in-memory registry for tool registration and schema lookup.
   - `ToolExecutor`: Async tool execution engine with runtime timing, exception containment, and error reporting.
   - `ToolResult`: Normalized execution output with `.to_event_payload()` producing event structures aligned with `docs/watchdog/monitoring-signals.md` and Koushik's `Watchdog`.
   - Builtin prototype tools: `CalculatorTool` and `EchoTool` for pipeline validation.

**Scope Audit & Cleanup:**
- **Audit Findings:** The core provider and tool prototype is lightweight and modular (~60-90 LOC per component) without premature dependencies.
- **Cleanup Performed:** Removed the extraneous feature-specific log file (`logs/feature_provider_tools.md`) to maintain the two-file logging architecture (`experimental_log.md` for personal/branch log, `logs/log.md` for shared team log).
- **Scope Preserved for Day 2+:** Intentionally deferred live vendor SDK integrations, production tool routing, dynamic provider fallback, and full Pathway streaming pipeline.

**Tests & Validation:**
- Ran `python -m unittest discover -s tests -p "test_*.py"` — 17 unit and integration tests passing.
- Validated provider generation, mock tool triggering, tool registry, async executor error handling, and watchdog anomaly detection compatibility.

**Impact & Current Status:**
Day 1 foundation prototype is complete and verified. The orchestration layer (`src/orchestration`) has clean interfaces to build against on Day 2.


### Date: 2026-08-17
**Experiment / Decision:**
Gateway, Orchestration, and Event Contract Foundation — Day 2

**Context:**
The gateway and orchestration layers required an event-driven foundation to decouple them from the API layer and the Watchdog system.

**Problem:**
We needed to establish the first stable Gateway/Event contract and make the mocked execution flow operational without prematurely adding complex Pathway streaming or heavy state persistence.

**Decision:**
- Gateway owns request-level lifecycle events.
- Orchestrator owns execution/provider/tool lifecycle events.
- Structured events are the shared contract between Gateway, Watchdog, API, and telemetry.
- State is currently in-memory and has a single owner.
- EventStream is currently an in-memory implementation.
- Full Pathway streaming is intentionally deferred to a later integration step.

**Impact:**
The Gateway → Orchestrator → Mock Execution pipeline is now operational and producing structured events. This establishes a clean contract that the rest of the team can build against.
>>>>>>> Stashed changes
