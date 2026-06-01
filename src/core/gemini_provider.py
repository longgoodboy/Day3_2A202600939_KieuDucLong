import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction is passed during model initialization or as a prefix
        # For simplicity in this lab, we'll prepend it if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        response = self.model.generate_content(full_prompt)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Gemini usage data is in response.usage_metadata
        content = response.text
        usage_metadata = getattr(response, "usage_metadata", None)
        usage = {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(usage_metadata, "total_token_count", 0)
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "gemini",
            "model": self.model_name,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        response = self.model.generate_content(full_prompt, stream=True)
        for chunk in response:
            yield chunk.text
