# Initial Watchdog Monitoring Signals

## Required Event Information

The Watchdog initially needs:

- request_id
- event_type
- timestamp
- tool_name
- status
- session_id
- tool_call_id

## Initial Monitoring Signals

- Request start and completion
- Request duration
- Tool-call frequency
- Tool-call sequence
- Tool execution status
- Event ordering

## Initial Anomaly Cases

### Repeated Tool Calls

Detect repeated calls to the same tool within one request.

Initial threshold: 5 calls.

### Timeout

Detect requests that remain active for too long.

Initial threshold: 30 seconds.

### Repeating Workflow Pattern

Detect simple repeating tool-call patterns that may indicate a workflow loop.

Example:

search → database → search → database → search → database

## Watchdog Output

The Watchdog should generate an alert containing:

- request_id
- anomaly_type
- timestamp
- detection details

## Note

These are initial Watchdog requirements and must be aligned with the final shared event schema.