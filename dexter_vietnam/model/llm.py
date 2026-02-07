"""
LLM Wrapper - Hỗ trợ OpenAI, Anthropic, Google Gemini
Dùng cho Agent Orchestrator
"""
from typing import Optional, List, Dict, Any
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Đảm bảo .env được load trước khi đọc API key
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)


class LLMWrapper:
    """Wrapper class for different LLM providers"""

    SUPPORTED_PROVIDERS = ("openai", "anthropic", "google")

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' not supported. "
                f"Use: {self.SUPPORTED_PROVIDERS}"
            )

        # Default models per provider
        default_models = {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "google": "gemini-2.0-flash",
        }
        self.model = model or default_models[self.provider]

        # Resolve API key
        key_env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        self.api_key = api_key or os.getenv(key_env_map[self.provider])
        if not self.api_key:
            raise ValueError(
                f"API key for {self.provider} not found. "
                f"Set {key_env_map[self.provider]} in .env"
            )

        self._init_client()

    def _init_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)

        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)

        elif self.provider == "google":
            from google import genai
            self._client = genai.Client(api_key=self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate text from LLM.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)

        Returns:
            Generated text
        """
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, system_prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt)
            elif self.provider == "google":
                return self._generate_google(prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM generation error ({self.provider}): {e}")
            raise

    def _generate_openai(self, prompt: str, system_prompt: Optional[str]) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str]) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)
        return response.content[0].text

    def _generate_google(self, prompt: str, system_prompt: Optional[str]) -> str:
        from google.genai import types

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

        response = self._client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        return response.text

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Generate structured JSON output from LLM."""
        json_instruction = (
            "\n\nIMPORTANT: Return ONLY valid JSON. "
            "No markdown, no code blocks, no explanation outside JSON."
        )
        raw = await self.generate(prompt + json_instruction, system_prompt)

        # Clean up potential markdown wrapping
        text = raw.strip()
        if text.startswith("```"):
            # Remove ```json ... ```
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM, raw: {text[:200]}")
            return {"raw_response": text, "parse_error": True}
