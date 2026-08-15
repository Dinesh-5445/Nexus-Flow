# Technical Integration Contracts

This document outlines the technical interfaces and boundaries between the different subsystems. 

The primary integration flow is:
```text
Client
  ↓
Sayan API / WebSocket Layer
  ↓
Dinesh Gateway Core
  ↓
Dinesh Orchestration
  ↓
Jyothi Provider / Tool Execution
  ↓
LLM / Tools
  ↓
Events
  ↓
Dinesh Pathway Event Stream
  ↓
Koushik Watchdog
  ↓
Alerts
  ↓
Harshit Telemetry / Dashboard
```

## Event Contracts
- **Dinesh** defines the shared event schema.
- **Jyothi** produces relevant execution events.
- **Koushik** consumes those events independently.
- **Harshit** consumes watchdog/telemetry information for monitoring.

## API Contracts (`services/api` ↔ `src/gateway`)
- **Sayan** exposes the gateway to client applications mapping REST/WebSocket messages to internal gateway request formats.

## Provider Interfaces (`src/orchestration` ↔ `src/providers`)
- Standardized execution request formatting allowing multiple LLM SDKs to be swapped under the hood. Returns standardized tool results and fires Pathway events.

## Watchdog Alerts (`src/watchdog` ↔ `services/telemetry`)
- Structured alert schema (e.g., loop detected, timeout) published by the watchdog and aggregated by the telemetry service.

## Dashboard Data (`services/api` / `services/telemetry` ↔ `frontend/dashboard`)
- Websocket channels pushing real-time latency, throughput, and formatted alerts to the frontend UI.
