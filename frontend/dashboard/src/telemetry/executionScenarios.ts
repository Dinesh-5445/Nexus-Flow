// Telemetry: Execution Scenarios (Day 9)
//
// Request bodies the dashboard can submit to POST /execute so both a
// successful and a failed execution can be exercised end to end from the UI.
//
// These are validation inputs, NOT API contract. They rely on how the current
// V1 backend behaves:
//   - MockProvider (src/providers/mock_provider.py) returns a calculator tool
//     call when the last message contains "calculate", otherwise plain text.
//   - Orchestrator (src/orchestration/executor.py) builds `LLMMessage(**msg)`
//     for each message, so a message without the required `content` raises and
//     the Gateway publishes a `failed` event.
// If those behaviors change, update this file.

export type ScenarioId = "success-plain" | "success-tool" | "failure-malformed";

export interface ExecutionScenario {
  id: ScenarioId;
  label: string;
  messages: Record<string, unknown>[];
}

export const EXECUTION_SCENARIOS: readonly ExecutionScenario[] = [
  {
    id: "success-plain",
    label: "Success — plain response",
    messages: [{ role: "user", content: "Dashboard live execution" }],
  },
  {
    id: "success-tool",
    label: "Success — with tool call",
    messages: [{ role: "user", content: "Please calculate 10 + 20" }],
  },
  {
    id: "failure-malformed",
    label: "Failure — malformed message",
    // Missing required `content`; the Orchestrator rejects it.
    messages: [{ role: "user" }],
  },
];

export function getScenario(id: ScenarioId): ExecutionScenario {
  const scenario = EXECUTION_SCENARIOS.find((s) => s.id === id);
  if (!scenario) {
    throw new Error(`Unknown execution scenario: ${id}`);
  }
  return scenario;
}