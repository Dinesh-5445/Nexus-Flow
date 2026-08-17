"""
Tool Execution Engine for NexusFlow.
Handles asynchronous execution of tool calls, error containment, execution timing,
and event generation.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from .base import ToolResult
from .registry import ToolRegistry
from ..providers.base import ToolCall


class ToolExecutor:
    """
    Executes tool calls asynchronously against a registered tool registry.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()

    async def execute_tool_call(
        self,
        tool_call: ToolCall,
        request_id: str = "",
        session_id: str = ""
    ) -> ToolResult:
        """
        Asynchronously executes a single ToolCall with error handling and timing.
        """
        tool = self.registry.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                status="failed",
                error=f"Tool '{tool_call.name}' is not registered.",
                execution_time_ms=0.0
            )

        start_time = time.perf_counter()
        try:
            # Parse arguments if stringified JSON was passed
            raw_args = tool_call.arguments
            if isinstance(raw_args, str):
                try:
                    args: Dict[str, Any] = json.loads(raw_args)
                except Exception as parse_err:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        status="failed",
                        error=f"Invalid arguments JSON: {parse_err}",
                        execution_time_ms=0.0
                    )
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            # Execute tool asynchronously
            result = await tool.execute(**args)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                status="completed",
                result=result,
                execution_time_ms=round(duration_ms, 2)
            )

        except TypeError as type_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                status="failed",
                error=f"Invalid tool arguments: {type_err}",
                execution_time_ms=round(duration_ms, 2)
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                status="failed",
                error=f"Tool execution failed: {exc}",
                execution_time_ms=round(duration_ms, 2)
            )

    async def execute_many(
        self,
        tool_calls: List[ToolCall],
        request_id: str = "",
        session_id: str = ""
    ) -> List[ToolResult]:
        """
        Concurrently executes a list of tool calls using asyncio.gather.
        """
        tasks = [
            self.execute_tool_call(tc, request_id=request_id, session_id=session_id)
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)
