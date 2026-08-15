# API Service

## Purpose
The primary REST and WebSocket interface.

## Responsibilities
Receiving client requests, validating schemas, handling errors, and communicating with the Python core gateway.

## Inputs/Outputs
- **Inputs:** Client/Dashboard requests.
- **Outputs:** Validated requests to `src/gateway`, and responses back to clients.\n