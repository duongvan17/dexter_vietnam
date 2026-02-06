"""
Tool Registry
TODO: Quản lý và đăng ký tất cả các tools
"""
from typing import Dict, Type
from .base import BaseTool

class ToolRegistry:
    """Registry for managing all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
    
    def register(self, tool_class: Type[BaseTool]):
        """Register a tool"""
        # TODO: Implement registration logic
        pass
    
    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name"""
        # TODO: Implement retrieval logic
        pass
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools"""
        # TODO: Return all tools
        pass
