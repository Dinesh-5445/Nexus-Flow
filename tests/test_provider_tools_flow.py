"""
Integration test for the Provider and Tool Execution flow.
Validates:
LLM Request -> Provider Abstraction -> Mock Provider -> Tool Call Request ->
Tool Registry / Executor -> Tool Result -> Event Emission compatible with Watchdog.
"""

import unittest
from src.providers import LLMMessage, MockProvider, ProviderConfig, ToolCall
from src.tools import CalculatorTool, ToolExecutor, ToolRegistry
from src.watchdog.detector import Watchdog
from src.events.schema import EventLifecycle


class TestProviderToolsFlow(unittest.IsolatedAsyncioTestCase):

    async def test_complete_provider_tool_watchdog_flow(self):
        # 1. Setup Tools & Registry
        registry = ToolRegistry()
        calc_tool = CalculatorTool()
        registry.register(calc_tool)
        executor = ToolExecutor(registry)

        # 2. Setup Provider
        provider = MockProvider(config=ProviderConfig(model_name="mock-gpt"))

        # 3. User request to provider
        messages = [
            LLMMessage(role="user", content="Can you calculate 10 + 20 for me?")
        ]
        tool_schemas = registry.get_schemas()

        # 4. Generate LLM response
        llm_response = await provider.generate(messages, tools=tool_schemas)

        # Verify LLM requested tool call
        self.assertTrue(llm_response.has_tool_calls)
        self.assertEqual(len(llm_response.tool_calls), 1)
        tool_call = llm_response.tool_calls[0]
        self.assertEqual(tool_call.name, "calculator")

        # 5. Execute Tool Call asynchronously
        request_id = "req-test-999"
        tool_result = await executor.execute_tool_call(tool_call, request_id=request_id)

        # Verify Tool execution success
        self.assertTrue(tool_result.is_success)
        self.assertEqual(tool_result.result, {"expression": "10 + 20", "result": 30})

        # 6. Format event payload and verify compatibility with Koushik's Watchdog
        event_payload = tool_result.to_event_payload(request_id=request_id)
        self.assertEqual(event_payload["event_type"], EventLifecycle.TOOL_EXECUTION.value)
        self.assertEqual(event_payload["tool_name"], "calculator")
        self.assertEqual(event_payload["status"], "completed")

        watchdog = Watchdog(repeated_call_threshold=5)
        alert = watchdog.process_event(event_payload)
        # Should not alert on 1 call
        self.assertIsNone(alert)

        # 7. Feed 4 more tool calls to verify anomaly detection boundary
        for _ in range(4):
            alert = watchdog.process_event(event_payload)

        # 5th call should trigger repeated tool call anomaly
        self.assertIsNotNone(alert)
        self.assertEqual(alert["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alert["tool_name"], "calculator")


if __name__ == "__main__":
    unittest.main()
