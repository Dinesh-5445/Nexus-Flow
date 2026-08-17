"""
Builtin Prototype Tools for NexusFlow.
Provides basic tools for prototyping, testing, and validation.
"""

from typing import Any, Dict
from .base import BaseTool


class CalculatorTool(BaseTool):
    """
    Evaluates basic mathematical expressions safely.
    """
    name = "calculator"
    description = "Evaluates basic mathematical expressions (e.g. '10 + 20', '5 * 4')."
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The math expression to evaluate."
            }
        },
        "required": ["expression"]
    }

    async def execute(self, expression: str, **kwargs: Any) -> Any:
        # Safe evaluation of basic arithmetic
        allowed_chars = set("0123456789+-*/(). %")
        if not all(c in allowed_chars for c in expression):
            raise ValueError(f"Disallowed characters in math expression: {expression}")
        try:
            # Simple eval with restricted globals/locals for basic math prototype
            result = eval(expression, {"__builtins__": {}}, {})
            return {"expression": expression, "result": result}
        except Exception as e:
            raise ValueError(f"Math evaluation error: {e}")


class EchoTool(BaseTool):
    """
    Echoes back the received message/arguments.
    Useful for testing parameter forwarding and pipeline verification.
    """
    name = "echo"
    description = "Echoes back provided input parameters."
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The text message to echo."
            }
        },
        "required": ["message"]
    }

    async def execute(self, message: str, **kwargs: Any) -> Any:
        return {"echo": message}
