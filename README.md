# Pathway-Powered Agentic Gateway

## Project Overview
The Pathway-Powered Agentic Gateway is a provider-agnostic AI orchestration gateway. It sits between client applications and LLM providers to manage an AI agent's reasoning process by capturing activity as a real-time event stream. An independent, asynchronous watchdog monitors this stream for anomalies like loops, timeouts, and repeated tool calls without blocking the main request path.

**Current Project Status:** Architecture/documentation/repository preparation phase — implementation has not yet been started.

## Problem Statement & Motivation
Most agent frameworks work well in demos but fail in production due to unreliable agent state, reasoning loops, repeated tool calls, timeouts, loss of state under concurrency, and poor observability. This leads to fragile orchestration and a lack of independent workflow monitoring. The core objective of this gateway is to treat agent activity as a continuous, recorded event stream rather than transient memory, allowing independent monitoring without interfering with request execution.

## System Architecture (Event-Driven)
```text
Client
   ↓
REST / WebSocket API
   ↓
Gateway
   ↓
Single-Agent Orchestration
   ↓
Provider Abstraction
   ↓
LLM Provider
   ↓
Tool Execution
   ↓
Event Generation
   ↓
Pathway Event Stream
   ↓
 ┌─────────────────────┐
 │                     │
 ▼                     ▼
Watchdog          State/Monitoring
 │                     │
 ▼                     ▼
Alerts             Telemetry
                       │
                       ▼
                   Dashboard
```

**Architecture Flow:**
- **Gateway** handles the main request path.
- **Provider Abstraction** allows provider independence.
- **Tool Execution** handles tool calls.
- **Pathway** acts as the real-time event-stream/state backbone.
- **Events** provide the shared system contract.
- **Watchdog** independently consumes the event stream and must not block the main request-processing path.
- **Alerts** flow into monitoring/telemetry.
- **Dashboard** visualizes system state, events, metrics, and alerts.

## Version 1 Scope
**Version 1 is a SINGLE-AGENT AI ORCHESTRATION GATEWAY.**
*Note: Version 1 is strictly single-agent. The existence of multiple engineering subsystems does not make it a multi-agent system.*
- Core gateway routing.
- One live AI provider via provider abstraction.
- Single-agent orchestration and tool execution (async).
- Pathway event streaming and state/event management via event schema.
- Independent watchdog for reasoning-loop detection, repeated tool-call detection, timeout detection, and workflow anomaly detection.
- REST API and WebSocket communication.
- Chat client and dashboard showing request latency, event throughput, and watchdog alert visualization.
- Telemetry/alert aggregation.
- Restart/recovery and end-to-end integration demonstration.

## Version 1 Exclusions
- Multiple live AI providers.
- Multi-agent workflows.
- Advanced checkpoint recovery.
- Full containerized deployment automation.
- Structured chaos testing.
- Horizontal scalability.

## Version 2 Roadmap
- Multiple interchangeable AI providers and dynamic provider routing.
- Multi-agent workflows.
- Checkpoint-based recovery.
- Structured chaos testing.
- Horizontal scalability and containerized deployment.
- Advanced telemetry, richer alert history, and state-graph visualization.

## Technology Stack
- **AI Infrastructure/Watchdog:** Python, asyncio, Pathway.
- **Web/API Platform:** Node.js, TypeScript, REST, WebSockets.
- **Frontend:** React, WebSocket client.
- **Telemetry Service:** Java (Optional, strictly scoped to telemetry).

## Team Contribution Model & Repository Structure
The repository is organized by software architecture, not by team members.
- `src/` - Core AI, orchestration, event, and watchdog logic.
- `services/` - Independent API and telemetry services.
- `frontend/` - Client and dashboard UI.
- `tests/` - System and end-to-end testing.
- `docs/` - Architectural documentation.
- `logs/` - Progress logging.
- `reference/` - Reference materials.

**Ownership:** See `CONTRIBUTION_GUIDE.md` for explicit team assignments.

## Logging Strategy
- `experimental_log.md` for architectural experiments, decisions, and benchmarks.
- `logs/log.md` for tracking meaningful implementation progress.

## Git Workflow
Branch-based development (e.g., `feature/gateway`). See `docs/git-workflow/README.md`.

## Testing Strategy
Subsystem testing by component owners; E2E integration testing coordinated across modules. See `docs/testing/README.md`.\n