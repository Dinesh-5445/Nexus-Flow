# System Architecture

## System Context
The Pathway-Powered Agentic Gateway is a single-agent architecture that orchestrates requests between a client and an AI provider while logging all activities as asynchronous events for an independent watchdog to analyze.

## Component Flow & Integration Boundaries
1. **Client Request Flow:** Client -> `services/api` (REST/WebSocket).
2. **Gateway Execution:** `services/api` -> `src/gateway` -> `src/orchestration`.
3. **Provider Execution:** `src/orchestration` -> `src/providers` -> `src/tools`.
4. **Event Flow:** `src/gateway` / `src/providers` -> `src/pathway` (Event Stream).
5. **Watchdog Flow:** `src/pathway` -> `src/watchdog`. The watchdog independently consumes events and does not block the main request path.
6. **Telemetry Flow:** `src/watchdog` emits alerts -> `services/telemetry`.
7. **Dashboard Flow:** `services/telemetry` & `services/api` -> `frontend/dashboard`.

## Version 1 Scope
Single-agent AI orchestration gateway with one provider abstraction, Pathway event streaming, an independent anomaly-detecting watchdog, a shared dashboard, and a telemetry aggregator. 

## Version 2 Scope
Multi-agent workflows, dynamic provider routing, structured chaos testing, advanced state-graph telemetry, horizontal scaling.\n