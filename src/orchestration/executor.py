"""
Orchestration Executor
Manages the execution flow of the AI agent, coordinating between Gateway and Providers.
"""

from typing import Any, Dict
from ..providers.base import BaseLLMProvider, LLMMessage
from ..tools.executor import ToolExecutor
from ..events.schema import Event, EventLifecycle
from ..events.stream import EventStream
# To avoid circular import, we just type hint GatewayRequest as Any if needed, but we can import it locally if careful.
# Instead, we just expect an object with a request_id and messages.

class Orchestrator:
    def __init__(self, provider: BaseLLMProvider, tool_executor: ToolExecutor, event_stream: EventStream):
        self.provider = provider
        self.tool_executor = tool_executor
        self.event_stream = event_stream

    async def execute_flow(self, request: Any) -> Dict[str, Any]:
        """
        Coordinates the execution of the agent workflow.
        `request` is expected to be a GatewayRequest.
        """
        # 1. Publish EXECUTION_STARTED
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.EXECUTION_STARTED,
                request_id=request.request_id,
                payload={"provider_model": self.provider.config.model_name}
            )
        )
        
        # 2. Convert messages and prepare tools
        llm_messages = [LLMMessage(**msg) for msg in request.messages]
        tools_schema = self.tool_executor.registry.get_schemas()
        
        # 3. Call Provider layer
        response = await self.provider.generate(messages=llm_messages, tools=tools_schema)
        
        final_result = {"content": response.content, "tool_results": []}
        
        # 4. Handle Tool Executions
        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                # Execute tool
                tool_result = await self.tool_executor.execute_tool_call(
                    tool_call, request_id=request.request_id, session_id=request.session_id
                )
                
                # Emit tool execution event using the standardized to_event_payload
                await self.event_stream.publish(
                    Event(
                        event_type=EventLifecycle.TOOL_EXECUTION,
                        request_id=request.request_id,
                        payload=tool_result.to_event_payload(
                            request_id=request.request_id, session_id=request.session_id
                        )
                    )
                )
                
                final_result["tool_results"].append(tool_result.to_dict())
                
        return final_result
