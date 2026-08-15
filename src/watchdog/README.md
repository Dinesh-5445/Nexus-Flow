# Watchdog

## Purpose
Independent event-stream anomaly detector.

## Responsibilities
Observing the Pathway event stream asynchronously without blocking the main request path. Detects reasoning loops, timeouts, and repeated tool calls.

## Inputs/Outputs
- **Inputs:** Pathway event stream.
- **Outputs:** Formatted alert events.\n