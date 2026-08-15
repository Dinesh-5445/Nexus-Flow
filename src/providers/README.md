# Providers

## Purpose
The AI provider abstraction layer.

## Responsibilities
Decouples the orchestration logic from specific LLM provider APIs. Manages provider configurations.

## Inputs/Outputs
- **Inputs:** Standardized LLM prompts from the orchestrator.
- **Outputs:** Standardized completions and tool call requests.

## Future Scope
Version 1 integrates one live provider. Version 2 will feature multiple interchangeable providers.\n