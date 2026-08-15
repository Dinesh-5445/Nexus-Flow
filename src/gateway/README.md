# Gateway

## Purpose
Core request routing layer for the system.

## Responsibilities
Handles the main request path, receiving parsed API requests and passing them to the orchestrator.

## Inputs/Outputs
- **Inputs:** Validated API requests from `services/api`.
- **Outputs:** Triggering orchestration flows; returning final AI responses.

## Future Scope
Handling session initialization and request lifecycle management for the single-agent pipeline.\n