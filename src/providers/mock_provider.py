"""
Mock LLM Provider for local development, tests, and CI.
Provides deterministic, configurable responses without requiring real API keys.
"""

from typing import Any, Dict, List, Optional
import uuid
from .base import BaseLLMProvider, LLMMessage, LLMResponse, ProviderConfig, ToolCall


class MockProvider(BaseLLMProvider):
    """
    Mock LLM Provider that returns pre-configured responses or predictable mock completions.
    """

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        predefined_responses: Optional[List[LLMResponse]] = None
    ):
        super().__init__(config)
        self.predefined_responses: List[LLMResponse] = predefined_responses or []
        self.call_history: List[Dict[str, Any]] = []

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generates a mock LLMResponse."""
        self.call_history.append({
            "messages": [m.to_dict() for m in messages],
            "tools": tools,
            "kwargs": kwargs
        })

        if self.predefined_responses:
            return self.predefined_responses.pop(0)

        # Default predictable behavior based on user prompt
        last_message = messages[-1].content if messages else ""
        
        # Check if the user prompt is asking to use a known mock tool
        if tools and "calculate" in last_message.lower():
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="calculator",
                        arguments={"expression": "10 + 20"}
                    )
                ],
                model=self.config.model_name,
                finish_reason="tool_calls",
                usage={"prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35},
                raw_response={"mock": True}
            )

        return LLMResponse(
            content=f"Mock response to: {last_message}",
            tool_calls=[],
            model=self.config.model_name,
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            raw_response={"mock": True}
        )
