"""
Integration tests for the Provider and Tool Execution flow.
Validates:
1. Success Case: Normal provider execution without tool calls.
2. Tool Execution Case: LLM Request -> Provider -> Tool Call -> Tool Execution -> Tool Result -> Orchestrator result -> Event emission.
3. Failure Cases: Tool execution runtime errors, missing/unavailable tools, invalid arguments, and provider exceptions.
"""

import unittest
import uuid
from src.providers import BaseLLMProvider, LLMMessage, LLMResponse, MockProvider, ProviderConfig, ToolCall
from src.tools import CalculatorTool, EchoTool, ToolExecutor, ToolRegistry
from src.events.schema import EventLifecycle
from src.events.stream import EventStream
from src.orchestration.executor import Orchestrator
from src.gateway.models import GatewayRequest
from src.gateway.router import GatewayRouter
from src.state.manager import StateManager
from src.tools.base import ToolResult



class TestProviderToolsFlow(unittest.IsolatedAsyncioTestCase):

    async def test_complete_provider_tool_watchdog_flow(self):
        """Validates provider tool-call generation, execution, and event payload formatting."""
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

        # 6. Format event payload and verify compatibility with shared event contract
        event_payload = tool_result.to_event_payload(request_id=request_id)
        self.assertEqual(event_payload["event_type"], EventLifecycle.TOOL_EXECUTION.value)
        self.assertEqual(event_payload["tool_name"], "calculator")
        self.assertEqual(event_payload["status"], "completed")

    async def test_provider_success_flow_without_tools(self):
        """A. SUCCESS CASE: Normal provider execution without tool calls succeeds and returns correct structure."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        provider = MockProvider(config=ProviderConfig(model_name="mock-gpt-4"))
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-success-001",
            session_id="sess-001",
            messages=[{"role": "user", "content": "Explain NexusFlow architecture"}]
        )

        result = await orchestrator.execute_flow(request)

        # Verify provider result structure
        self.assertIsNotNone(result)
        self.assertIn("content", result)
        self.assertEqual(result["content"], "Mock response to: Explain NexusFlow architecture")
        self.assertEqual(result["tool_results"], [])

        # Verify emitted lifecycle events (EXECUTION_STARTED -> LLM_EXECUTION)
        events = event_stream.published_events
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[0].payload["provider_model"], "mock-gpt-4")
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        self.assertEqual(events[1].payload["model"], "mock-gpt-4")

    async def test_provider_tool_execution_flow_via_orchestrator(self):
        """B. TOOL EXECUTION CASE: Full flow with tool execution consumed and formatted by Orchestrator."""
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        executor = ToolExecutor(registry)
        provider = MockProvider(config=ProviderConfig(model_name="mock-tool-agent"))
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        # User prompt that triggers CalculatorTool in MockProvider
        request = GatewayRequest(
            request_id="req-tool-002",
            session_id="sess-002",
            messages=[{"role": "user", "content": "Please calculate 10 + 20"}]
        )

        result = await orchestrator.execute_flow(request)

        # Verify final result contains tool results
        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["tool_name"], "calculator")
        self.assertEqual(tool_res["status"], "completed")
        self.assertEqual(tool_res["result"], {"expression": "10 + 20", "result": 30})

        # Verify events emitted (EXECUTION_STARTED -> LLM_EXECUTION -> TOOL_EXECUTION)
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        self.assertEqual(events[2].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[2].payload["tool_name"], "calculator")
        self.assertEqual(events[2].payload["status"], "completed")

    async def test_provider_tool_execution_failure_handling(self):
        """C1. FAILURE CASE: Tool execution failure (e.g. division by zero) is safely contained and reported."""
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        executor = ToolExecutor(registry)

        # Program mock provider to request a calculation that divides by zero
        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_err_1", name="calculator", arguments={"expression": "10 / 0"})
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-fail-001",
            session_id="sess-fail-001",
            messages=[{"role": "user", "content": "Calculate 10 / 0"}]
        )

        result = await orchestrator.execute_flow(request)

        # Execution completes without crashing; tool failure is captured in tool_results
        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("division by zero", tool_res["error"])

        # Event stream captures tool execution failure
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        tool_event = events[2]
        self.assertEqual(tool_event.event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(tool_event.payload["status"], "failed")
        self.assertIn("division by zero", tool_event.payload["error"])

    async def test_provider_unavailable_tool_failure_handling(self):
        """C2. FAILURE CASE: Requesting an unregistered tool returns failed status."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_unavail_1", name="weather_tool", arguments={"city": "Tokyo"})
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-fail-002",
            session_id="sess-fail-002",
            messages=[{"role": "user", "content": "What is the weather?"}]
        )

        result = await orchestrator.execute_flow(request)

        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("is not registered", tool_res["error"])

        # Event stream reflects unregistered tool error
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        self.assertEqual(events[2].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[2].payload["status"], "failed")
        self.assertIn("is not registered", events[2].payload["error"])

    async def test_provider_invalid_arguments_failure_handling(self):
        """C3. FAILURE CASE: Invalid arguments to a tool return failed status."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        executor = ToolExecutor(registry)

        # EchoTool expects 'message', but we pass unexpected args
        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_inv_1", name="echo", arguments={"wrong_param": "hello"})
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-fail-003",
            session_id="sess-fail-003",
            messages=[{"role": "user", "content": "Echo test"}]
        )

        result = await orchestrator.execute_flow(request)

        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("Invalid tool arguments", tool_res["error"])

        # Event stream reflects invalid tool arguments error
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        self.assertEqual(events[2].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[2].payload["status"], "failed")
        self.assertIn("Invalid tool arguments", events[2].payload["error"])

    async def test_provider_exception_propagation(self):
        """C4. FAILURE CASE: Provider-level exception propagates cleanly to caller/orchestrator."""
        class FailingProvider(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise ConnectionError("LLM Provider unreachable")

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        provider = FailingProvider(config=ProviderConfig(model_name="failing-model"))
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-fail-004",
            session_id="sess-fail-004",
            messages=[{"role": "user", "content": "Hello"}]
        )

        with self.assertRaises(ConnectionError) as ctx:
            await orchestrator.execute_flow(request)

        self.assertIn("LLM Provider unreachable", str(ctx.exception))

        events = event_stream.published_events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)

    async def test_multiple_tool_calls_flow_via_orchestrator(self):
        """D1. MULTIPLE TOOLS: Orchestrator executes multiple tool calls from a single LLMResponse in order."""
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(EchoTool())
        executor = ToolExecutor(registry)

        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_multi_1", name="calculator", arguments={"expression": "100 + 200"}),
                        ToolCall(id="call_multi_2", name="echo", arguments={"message": "multi tool success"})
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-multi-001",
            session_id="sess-multi-001",
            messages=[{"role": "user", "content": "Calculate and echo"}]
        )

        result = await orchestrator.execute_flow(request)

        # Verify both tool results are returned in order
        self.assertEqual(len(result["tool_results"]), 2)
        res1 = result["tool_results"][0]
        res2 = result["tool_results"][1]

        self.assertEqual(res1["tool_call_id"], "call_multi_1")
        self.assertEqual(res1["tool_name"], "calculator")
        self.assertEqual(res1["status"], "completed")
        self.assertEqual(res1["result"], {"expression": "100 + 200", "result": 300})

        self.assertEqual(res2["tool_call_id"], "call_multi_2")
        self.assertEqual(res2["tool_name"], "echo")
        self.assertEqual(res2["status"], "completed")
        self.assertEqual(res2["result"], {"echo": "multi tool success"})

        # Verify events: EXECUTION_STARTED -> LLM_EXECUTION -> TOOL_EXECUTION (1) -> TOOL_EXECUTION (2)
        events = event_stream.published_events
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[1].event_type, EventLifecycle.LLM_EXECUTION)
        self.assertEqual(events[2].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[2].payload["tool_call_id"], "call_multi_1")
        self.assertEqual(events[3].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[3].payload["tool_call_id"], "call_multi_2")

    async def test_tool_execution_stringified_json_arguments(self):
        """D2. ARGUMENT PARSING: ToolExecutor parses stringified JSON arguments passed by provider."""
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        executor = ToolExecutor(registry)

        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_str_1", name="calculator", arguments='{"expression": "50 * 2"}')
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-str-001",
            session_id="sess-str-001",
            messages=[{"role": "user", "content": "Multiply 50 * 2"}]
        )

        result = await orchestrator.execute_flow(request)

        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["status"], "completed")
        self.assertEqual(tool_res["result"], {"expression": "50 * 2", "result": 100})

    async def test_tool_execution_malformed_json_arguments_failure(self):
        """D3. ARGUMENT FAILURE: Malformed JSON string arguments safely return failed ToolResult."""
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        executor = ToolExecutor(registry)

        provider = MockProvider(
            predefined_responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_bad_json_1", name="calculator", arguments='{bad_json_str')
                    ],
                    finish_reason="tool_calls"
                )
            ]
        )
        event_stream = EventStream()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-bad-json-001",
            session_id="sess-bad-json-001",
            messages=[{"role": "user", "content": "Test malformed JSON"}]
        )

        result = await orchestrator.execute_flow(request)

        self.assertEqual(len(result["tool_results"]), 1)
        tool_res = result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("Invalid arguments JSON", tool_res["error"])

        # Verify event stream reflects failure
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[2].event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(events[2].payload["status"], "failed")
        self.assertIn("Invalid arguments JSON", events[2].payload["error"])

    async def test_provider_failure_with_gateway_router(self):
        """D4. PROVIDER FAILURE END-TO-END: Provider exception caught by GatewayRouter, sets failed state and emits FAILED event."""
        class DowntimeProvider(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise RuntimeError("503 Service Unavailable: Provider downstream error")

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        provider = DowntimeProvider(config=ProviderConfig(model_name="unstable-model"))
        event_stream = EventStream()
        state_manager = StateManager()
        orchestrator = Orchestrator(provider=provider, tool_executor=executor, event_stream=event_stream)
        gateway = GatewayRouter(orchestrator=orchestrator, state_manager=state_manager, event_stream=event_stream)

        request = GatewayRequest(
            request_id="req-gw-fail-001",
            session_id="sess-gw-fail-001",
            messages=[{"role": "user", "content": "Hello"}]
        )

        response = await gateway.handle_request(request)

        # Verify Gateway response status
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.request_id, "req-gw-fail-001")
        self.assertIn("503 Service Unavailable", response.error)

        # Verify StateManager state
        state = state_manager.get_state("req-gw-fail-001")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")
        self.assertIn("503 Service Unavailable", state.error)

        # Verify emitted events: REQUEST_RECEIVED -> EXECUTION_STARTED -> FAILED
        events = event_stream.published_events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventLifecycle.REQUEST_RECEIVED)
        self.assertEqual(events[1].event_type, EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(events[2].event_type, EventLifecycle.FAILED)
        self.assertIn("503 Service Unavailable", events[2].payload["error"])

    def test_tool_result_and_event_contract_field_conformance(self):
        """D5. CONTRACT CONFORMANCE: Verifies strict conformance of ToolResult.to_dict() and to_event_payload()."""
        tool_result = ToolResult(
            tool_call_id="call_strict_001",
            tool_name="calculator",
            status="completed",
            result={"expression": "1 + 1", "result": 2},
            error=None,
            execution_time_ms=5.42
        )

        # 1. Test to_dict structure
        d = tool_result.to_dict()
        self.assertEqual(set(d.keys()), {"tool_call_id", "tool_name", "status", "result", "error", "execution_time_ms"})
        self.assertEqual(d["tool_call_id"], "call_strict_001")
        self.assertEqual(d["tool_name"], "calculator")
        self.assertEqual(d["status"], "completed")
        self.assertEqual(d["result"], {"expression": "1 + 1", "result": 2})
        self.assertIsNone(d["error"])
        self.assertEqual(d["execution_time_ms"], 5.42)

        # 2. Test to_event_payload structure
        payload = tool_result.to_event_payload(request_id="req-strict-001", session_id="sess-strict-001")
        expected_keys = {
            "request_id", "event_type", "timestamp", "tool_name",
            "status", "session_id", "tool_call_id", "execution_time_ms", "error"
        }
        self.assertEqual(set(payload.keys()), expected_keys)
        self.assertEqual(payload["request_id"], "req-strict-001")
        self.assertEqual(payload["event_type"], EventLifecycle.TOOL_EXECUTION.value)
        self.assertEqual(payload["session_id"], "sess-strict-001")
        self.assertEqual(payload["tool_name"], "calculator")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["tool_call_id"], "call_strict_001")
        self.assertEqual(payload["execution_time_ms"], 5.42)
        self.assertIsNone(payload["error"])
        self.assertIsInstance(payload["timestamp"], float)


if __name__ == "__main__":
    unittest.main()
