"""
Tool Registry for NexusFlow.
Manages tool registration, lookup, and schema generation for LLMs.
"""

from typing import Any, Dict, List, Optional
from .base import BaseTool


class ToolRegistry:
    """
    Central registry for managing tools available to the AI agent.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance. Overwrites existing tool if name collides."""
        if not tool.name:
            raise ValueError("Tool name must not be empty.")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregisters a tool by name if present."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool instance by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Checks if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns the function calling schemas for all registered tools."""
        return [tool.to_schema() for tool in self._tools.values()]
