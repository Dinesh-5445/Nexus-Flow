"""
Unit tests for the Tool Abstraction and Execution Engine.
"""

import unittest
from src.providers.base import ToolCall
from src.tools.base import BaseTool, ToolResult
from src.tools.builtin import CalculatorTool, EchoTool
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry


class TestTools(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register(CalculatorTool())
        self.registry.register(EchoTool())
        self.executor = ToolExecutor(self.registry)

    def test_tool_registry(self):
        self.assertTrue(self.registry.has("calculator"))
        self.assertTrue(self.registry.has("echo"))
        self.assertFalse(self.registry.has("nonexistent"))

        schemas = self.registry.get_schemas()
        self.assertEqual(len(schemas), 2)
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("calculator", names)
        self.assertIn("echo", names)

    def test_tool_schema_structure(self):
        calc = CalculatorTool()
        schema = calc.to_schema()
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "calculator")
        self.assertIn("expression", schema["function"]["parameters"]["properties"])

    async def test_calculator_execution_success(self):
        calc = CalculatorTool()
        res = await calc.execute(expression="15 * 3")
        self.assertEqual(res, {"expression": "15 * 3", "result": 45})

    async def test_calculator_execution_invalid(self):
        calc = CalculatorTool()
        with self.assertRaises(ValueError):
            await calc.execute(expression="import os")

    async def test_echo_execution_success(self):
        echo = EchoTool()
        res = await echo.execute(message="hello world")
        self.assertEqual(res, {"echo": "hello world"})

    async def test_executor_successful_tool_call(self):
        tool_call = ToolCall(id="call_1", name="calculator", arguments={"expression": "100 / 4"})
        result: ToolResult = await self.executor.execute_tool_call(
            tool_call, request_id="req-123", session_id="sess-abc"
        )

        self.assertTrue(result.is_success)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result, {"expression": "100 / 4", "result": 25.0})
        self.assertIsNone(result.error)
        self.assertGreaterEqual(result.execution_time_ms, 0.0)

    async def test_executor_missing_tool(self):
        tool_call = ToolCall(id="call_2", name="unknown_tool", arguments={})
        result = await self.executor.execute_tool_call(tool_call, request_id="req-123")

        self.assertFalse(result.is_success)
        self.assertEqual(result.status, "failed")
        self.assertIn("is not registered", result.error)

    async def test_executor_invalid_arguments(self):
        # Passing wrong argument type / missing required argument
        tool_call = ToolCall(id="call_3", name="calculator", arguments={"wrong_arg": 123})
        result = await self.executor.execute_tool_call(tool_call, request_id="req-123")

        self.assertFalse(result.is_success)
        self.assertEqual(result.status, "failed")
        self.assertIn("Invalid tool arguments", result.error)

    async def test_executor_concurrent_execution(self):
        calls = [
            ToolCall(id="c1", name="calculator", arguments={"expression": "2 + 2"}),
            ToolCall(id="c2", name="echo", arguments={"message": "async works"}),
            ToolCall(id="c3", name="calculator", arguments={"expression": "10 * 10"}),
        ]
        results = await self.executor.execute_many(calls, request_id="req-bulk")
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.is_success for r in results))
        self.assertEqual(results[0].result["result"], 4)
        self.assertEqual(results[1].result["echo"], "async works")
        self.assertEqual(results[2].result["result"], 100)

    def test_tool_result_to_event_payload(self):
        result = ToolResult(
            tool_call_id="call_99",
            tool_name="calculator",
            status="completed",
            result={"result": 42},
            execution_time_ms=1.23
        )
        event = result.to_event_payload(request_id="req-001", session_id="sess-001")
        self.assertEqual(event["request_id"], "req-001")
        self.assertEqual(event["event_type"], "tool_called")
        self.assertEqual(event["tool_name"], "calculator")
        self.assertEqual(event["status"], "completed")
        self.assertEqual(event["tool_call_id"], "call_99")
        self.assertEqual(event["session_id"], "sess-001")
        self.assertIn("timestamp", event)


if __name__ == "__main__":
    unittest.main()
