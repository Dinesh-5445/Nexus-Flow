# Team Contribution Guide

This document defines the primary ownership and integration dependencies for the team. The physical repository is structured by software architecture, while this guide clarifies who works on what. 

All five team members own a complete, independently developable area and contribute production code. No member is documentation-only. The team does NOT work by modifying each other's internal implementation unnecessarily; integration happens through APIs, events, schemas, interfaces, WebSockets, and defined contracts. Everyone helps each other with integration, debugging, and reviews.

## Ownership Matrix

| Workstream / Component | Primary Owner | Integration / Collaboration |
|---|---|---|
| Gateway Core | Dinesh | Sayan |
| Single-Agent Orchestration | Dinesh | Jyothi |
| Pathway Integration | Dinesh | Koushik |
| Event Schema / Contracts | Dinesh | All |
| State Management | Dinesh | Koushik |
| Provider Abstraction | Jyothi | Dinesh |
| LLM Integration | Jyothi | Dinesh |
| Tool Execution Engine | Jyothi | Dinesh + Koushik |
| Async Tool Execution | Jyothi | Dinesh |
| Watchdog | Koushik | Dinesh |
| Event-Stream Analysis | Koushik | Dinesh |
| Anomaly Detection | Koushik | Dinesh |
| Watchdog Evaluation / Benchmarking | Koushik | Dinesh |
| REST API | Sayan | Dinesh |
| WebSocket Server | Sayan | Harshit |
| Chat Client | Harshit | Sayan |
| Dashboard | Sayan + Harshit | Shared |
| Telemetry / Alert Aggregation | Harshit | Koushik |
| Module-Level Testing | Each owner | — |
| End-to-End Integration | Dinesh | Sayan + Harshit + all owners |

## AI Infrastructure Workstreams

The AI infrastructure is divided into three independently developable and substantial workstreams:

```text
                    AI INFRASTRUCTURE
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       DINESH           JYOTHI           KOUSHIK
          │                │                │
          ▼                ▼                ▼
 Gateway /            Provider /       Watchdog /
 Orchestration        Tools            Anomaly Detection
 Pathway              LLM Integration  Event Analysis
 State                Async Execution  Evaluation
 Events               Configuration    Benchmarking
```

### Dinesh
**Primary Area:** Architecture, Pathway Integration & Orchestration

**Responsibilities:**
- Overall system architecture
- Integration contracts and boundaries
- Shared event schema
- Pathway integration
- State management
- Core orchestration
- Single-agent execution flow for Version 1
- Critical AI infrastructure implementation
- Cross-module integration
- Difficult technical debugging and helping teammates resolve technical problems
- PR/code review
- Final end-to-end integration

*Note: Dinesh is NOT only an architect; he is a primary production-code contributor implementing his own core subsystem. His integration responsibility means ensuring independently developed components work together, not doing all implementation himself.*

**Primary Repository Areas:** `src/gateway/`, `src/orchestration/`, `src/pathway/`, `src/events/`, `src/state/`

**Version 1 Expected Outcome:** Working gateway core with event schema, orchestration, Pathway integration, state management, and end-to-end integration.

### Jyothi Kiran
**Primary Area:** AI Subsystem — Provider Abstraction & Tool Execution

**Responsibilities:**
- Provider abstraction layer
- LLM integration
- Provider configuration
- Tool execution engine
- Asynchronous tool execution
- Provider/tool interfaces
- Tool-calling protocols
- Error handling around provider/tool execution
- Subsystem testing and subsystem benchmarks
- Integration with gateway contracts
- Event emission required by the shared event model

*Note: Jyothi owns a complete AI subsystem, independently developable and substantial. Jyothi's provider/tool execution must emit the events required by the shared event contract defined by Dinesh.*

**Primary Repository Areas:** `src/providers/`, `src/tools/`

**Version 1 Expected Outcome:** Working provider-agnostic tool execution subsystem with LLM integration, asynchronous execution, configuration, tests, and benchmarks.

### Koushik
**Primary Area:** AI Subsystem — Watchdog & Anomaly Detection

**Responsibilities:**
- Independent watchdog process
- Event-stream consumption
- Reasoning-loop detection
- Repeated-tool-call detection
- Timeout detection
- Workflow anomaly detection
- Event pattern analysis
- Alert generation
- Watchdog evaluation, benchmarking, testing, and logging
- Reliability validation

*Note: The watchdog is a substantial AI infrastructure subsystem with its own algorithms, event consumption, detection logic, evaluation, and testing responsibilities. It is an independent event-stream consumer that must NOT directly couple to orchestration internals or block the primary request path.*

**Primary Repository Area:** `src/watchdog/`

**Version 1 Expected Outcome:** Working watchdog that detects loops, repeated tool calls, and timeouts and is validated through evaluation and benchmarks.

## Web / Full-Stack Workstreams

### Sayan
**Primary Area:** Web/API Platform & Gateway Interface

**Responsibilities:**
- REST API
- WebSocket server
- API contracts and request/response schemas
- Validation and error handling
- Gateway-facing service layer
- API integration with gateway core
- WebSocket communication and backend logic
- API testing and frontend integration interfaces

*Technology:* Node.js + TypeScript

**Primary Repository Area:** `services/api/`

**Version 1 Expected Outcome:** Working REST/WebSocket API and gateway-facing service layer.

### Harshit
**Primary Area:** Frontend, Dashboard & Monitoring Platform

**Responsibilities:**
- Chat client
- Frontend and Dashboard
- Real-time UI
- WebSocket client integration
- Monitoring interface
- Telemetry integration and alert visualization
- Telemetry/alert aggregation service
- Monitoring backend logic
- Frontend testing and real-time system visualization

*Technology:* Modern frontend framework (e.g., React). Telemetry/alert aggregation may use Java if appropriate (Java must remain scoped to the telemetry/alert-aggregation service and not enter the core AI infrastructure).

**Primary Repository Areas:** `frontend/client/`, `services/telemetry/`

**Version 1 Expected Outcome:** Working chat client, dashboard, monitoring interface, and telemetry/alert-aggregation service.

### Dashboard Ownership (Shared)
The dashboard is shared between Sayan and Harshit.

**Primary Repository Area:** `frontend/dashboard/`

**Sayan primarily contributes:**
- API integration
- WebSocket integration
- Backend data exposure
- Real-time service communication
- Dashboard data contracts

**Harshit primarily contributes:**
- UI and visualization
- Telemetry and monitoring views
- Alert visualization
- Client-side WebSocket integration

Both can modify the dashboard when required by their respective integration work.

## Integration Dependency Flow
1. Define shared event schema and service/API contracts.
2. Establish gateway/API interfaces between Dinesh's core and Sayan's API layer.
3. Jyothi implements provider abstraction and basic tool execution.
4. Dinesh implements Pathway event ingestion.
5. Koushik implements independent watchdog consumption and anomaly detection.
6. Sayan implements REST/WebSocket service integration.
7. Harshit builds the chat client, dashboard, and telemetry service.
8. Integrate telemetry with watchdog alerts.
9. Run end-to-end tests.
10. Demonstrate normal execution → anomaly → recovery.
