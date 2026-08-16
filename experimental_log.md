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

---

### Date: 2026-08-16
**Experiment / Decision:**
Watchdog Day 1 Prototype & Anomaly Detection Architecture

**Context:**
The Watchdog subsystem (owned by Koushik) requires independent event-stream observation to detect orchestration anomalies (e.g., repeated tool calls, reasoning loops, timeouts).

**Problem:**
Tight coupling of anomaly checks inside the primary orchestration path would introduce latency, increase request failure risk, and obscure execution telemetry.

**Initial approach:**
Inline anomaly checking within orchestrator loops vs. decoupled event-stream analysis.

**Decision:**
Implement an independent `Watchdog` component ([`src/watchdog/detector.py`](file:///c:/Users/koushik/Desktop/pythonprojects/Nexus-Flow/src/watchdog/detector.py)) that consumes event dicts without modifying gateway execution state.

**Key Prototype Results & Scope:**
- Defined core monitoring signals (`request_id`, `event_type`, `timestamp`, `tool_name`, `status`, `session_id`, `tool_call_id`) and anomaly specs in [`docs/watchdog/monitoring-signals.md`](file:///c:/Users/koushik/Desktop/pythonprojects/Nexus-Flow/docs/watchdog/monitoring-signals.md).
- Implemented `collections.Counter`-based repeated tool-call detection flagging repetitions at threshold >= 5.
- Structured standard anomaly alert dict payload: `{"request_id": ..., "anomaly_type": "repeated_tool_call", "tool_name": ..., "count": ...}`.
- Added executable mock event driver ([`detector.py:L35-L84`](file:///c:/Users/koushik/Desktop/pythonprojects/Nexus-Flow/src/watchdog/detector.py#L35-L84)) demonstrating alert generation across 5 sequential mock events.

**Reason:**
Establishes a functional, non-blocking proof-of-concept for anomaly detection prior to integration with Pathway event stream and Dinesh's final event schema.

**Impact:**
Validated Day 1 Watchdog feasibility; ready for integration with Pathway event ingestion and alert aggregation services.