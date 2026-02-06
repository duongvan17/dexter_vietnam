"""
Base Tool class
TODO: Implement base class cho tất cả các tools
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
        """Return tool description"""
        pass
    
    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        pass
