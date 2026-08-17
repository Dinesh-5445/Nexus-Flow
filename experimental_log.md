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

---

### Date: 2026-08-17
**Experiment / Decision:**
Watchdog Day 2 — Adaptation to Dinesh's Initial Event Format

**Context:**
The Day 1 Watchdog prototype used an initial event representation and needed to be adapted to the event structure now available from Dinesh's implementation.

**Work Completed:**
- Adapted [`Watchdog.process_event()`](file:///c:/Users/koushik/Desktop/pythonprojects/Nexus-Flow/src/watchdog/detector.py) to safely parse Dinesh's current event payload representation (`ToolResult.to_event_payload()`).
- Preserved existing `collections.Counter` repeated-tool-call detection logic and threshold configuration (>= 5 calls).
- Added dedicated test suite [`tests/test_watchdog.py`](file:///c:/Users/koushik/Desktop/pythonprojects/Nexus-Flow/tests/test_watchdog.py) validating normal tool call execution, repeated-call detection, request isolation, and non-tool event filtering.

**Validation:**
```text
python -m pytest tests/test_watchdog.py -v
5 passed in 0.03s
```
- `test_ignore_non_tool_called_events`: PASSED (non-tool events ignored)
- `test_integration_with_tool_result_to_event_payload`: PASSED (integration with `ToolResult.to_event_payload()`)
- `test_normal_tool_calls_no_alert`: PASSED (normal tool calls below threshold produce no alert)
- `test_repeated_tool_calls_triggers_alert`: PASSED (repeated tool calls at threshold trigger alert)
- `test_request_isolation`: PASSED (independent request tracking without cross-contamination)

**Scope Limitations:**
Day 2 explicitly did NOT implement:
- Timeout detection
- Repeating workflow / sequence loop detection
- Additional anomaly types or scoring algorithms
- Changes to Dinesh's shared event schema or other teammate subsystems

**Impact:**
The existing Watchdog repeated-tool-call prototype is now fully validated against Dinesh's current event representation and ready for Pathway event stream integration.