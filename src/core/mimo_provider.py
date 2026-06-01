import os
import time
from typing import Any, Dict, Generator, Optional

from openai import OpenAI

from src.core.llm_provider import LLMProvider


class MiMoProvider(LLMProvider):
    """LLM provider for Xiaomi MiMo using the OpenAI-compatible API."""

    DEFAULT_BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
    DEFAULT_MODEL = "mimo-v2.5-pro"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(model_name=model_name, api_key=api_key)
        self.provider_name = "mimo"
        self.base_url = base_url or os.getenv("MIMO_BASE_URL", self.DEFAULT_BASE_URL)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Produce a non-streaming MiMo chat completion."""
        start_time = time.time()
        messages = self._build_messages(prompt, system_prompt)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        content = response.choices[0].message.content or ""

        return {
            "content": content,
            "usage": self._extract_usage(response),
            "latency_ms": latency_ms,
            "provider": "mimo",
            "model": self.model_name,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Produce a streaming MiMo chat completion."""
        messages = self._build_messages(prompt, system_prompt)

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                yield delta.content

    def _build_messages(self, prompt: str, system_prompt: Optional[str]) -> list[dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _extract_usage(self, response: Any) -> Dict[str, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
