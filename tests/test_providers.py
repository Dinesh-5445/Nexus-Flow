"""
Unit tests for the Provider Abstraction Layer.
"""

import os
import unittest
from unittest.mock import patch

from src.providers.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    ProviderConfig,
    ToolCall,
)
from src.providers.mock_provider import MockProvider


class TestProviders(unittest.IsolatedAsyncioTestCase):

    def test_llm_message_to_dict(self):
        msg = LLMMessage(role="user", content="Hello NexusFlow")
        self.assertEqual(msg.to_dict(), {"role": "user", "content": "Hello NexusFlow"})

        msg_tool = LLMMessage(
            role="tool",
            content='{"result": 42}',
            name="calculator",
            tool_call_id="call_123"
        )
        expected = {
            "role": "tool",
            "content": '{"result": 42}',
            "name": "calculator",
            "tool_call_id": "call_123"
        }
        self.assertEqual(msg_tool.to_dict(), expected)

    def test_llm_response_properties(self):
        resp_text = LLMResponse(content="Simple answer", finish_reason="stop")
        self.assertFalse(resp_text.has_tool_calls)

        resp_tools = LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="c1", name="search", arguments={"query": "test"})],
            finish_reason="tool_calls"
        )
        self.assertTrue(resp_tools.has_tool_calls)
        self.assertEqual(len(resp_tools.tool_calls), 1)
        self.assertEqual(resp_tools.tool_calls[0].name, "search")

    def test_provider_config_from_env(self):
        with patch.dict(os.environ, {
            "TEST_PROVIDER_API_KEY": "secret-key-xyz",
            "TEST_PROVIDER_MODEL_NAME": "test-model-v1",
            "TEST_PROVIDER_TEMPERATURE": "0.2",
            "TEST_PROVIDER_MAX_TOKENS": "512",
            "TEST_PROVIDER_TIMEOUT_SECONDS": "15.0"
        }, clear=False):
            config = ProviderConfig.from_env(prefix="TEST_PROVIDER_")
            self.assertEqual(config.api_key, "secret-key-xyz")
            self.assertEqual(config.model_name, "test-model-v1")
            self.assertEqual(config.temperature, 0.2)
            self.assertEqual(config.max_tokens, 512)
            self.assertEqual(config.timeout_seconds, 15.0)

    async def test_mock_provider_text_generation(self):
        provider = MockProvider(config=ProviderConfig(model_name="mock-v1"))
        messages = [LLMMessage(role="user", content="Hello AI")]

        response = await provider.generate(messages)
        self.assertIsNotNone(response.content)
        self.assertIn("Mock response to: Hello AI", response.content)
        self.assertFalse(response.has_tool_calls)
        self.assertEqual(response.model, "mock-v1")
        self.assertEqual(len(provider.call_history), 1)

    async def test_mock_provider_tool_triggering(self):
        provider = MockProvider(config=ProviderConfig(model_name="mock-v1"))
        messages = [LLMMessage(role="user", content="Please calculate 10 + 20")]
        tools = [{"type": "function", "function": {"name": "calculator"}}]

        response = await provider.generate(messages, tools=tools)
        self.assertTrue(response.has_tool_calls)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "calculator")
        self.assertEqual(response.tool_calls[0].arguments, {"expression": "10 + 20"})
        self.assertEqual(response.finish_reason, "tool_calls")

    async def test_mock_provider_predefined_responses(self):
        custom_resp = LLMResponse(content="Predefined message", finish_reason="stop")
        provider = MockProvider(predefined_responses=[custom_resp])
        
        resp = await provider.generate([LLMMessage(role="user", content="any")])
        self.assertEqual(resp.content, "Predefined message")


if __name__ == "__main__":
    unittest.main()
