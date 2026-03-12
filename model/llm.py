"""
LLM Wrapper - OpenRouter only, synchronous.
"""
from typing import Optional, List, Dict, Any
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)


class LLMWrapper:

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs,  # ignore legacy provider arg etc.
    ):
        self.provider = "openrouter"
        self.model = model or os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found. Set it in .env or pass via api_key."
            )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:

        msgs = list(messages)
        if system_prompt and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": system_prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=msgs,
            tools=tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append({
                    "id": tc.id,
                    "function_name": tc.function.name,
                    "arguments": args,
                })

        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "raw": response,
        }
