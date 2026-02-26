"""
Base Tool class
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Base class for all tools"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Return tool name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return tool description for LLM"""
        pass

    @abstractmethod
    def get_actions(self) -> Dict[str, str]:
        """Return supported actions: {action_name: short_description}"""
        pass
    
    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        pass
