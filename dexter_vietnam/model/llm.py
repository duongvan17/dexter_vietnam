"""
LLM Wrapper
TODO: Integrate với OpenAI, Anthropic, Google Gemini
"""
from typing import Optional

class LLMWrapper:
    """Wrapper class for different LLM providers"""
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4"):
        self.provider = provider
        self.model = model
        # TODO: Initialize LLM client
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text from LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
        
        Returns:
            Generated text
        """
        # TODO: Implement generation logic
        pass
    
    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """Generate structured JSON output"""
        # TODO: Implement
        pass
