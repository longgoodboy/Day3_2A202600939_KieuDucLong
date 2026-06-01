from typing import Any, Dict

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class Chatbot:
    """Baseline chatbot that answers with exactly one LLM call and no tools."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user_input: str) -> str:
        """Run one LLM completion and return the generated content."""
        logger.log_event(
            "CHATBOT_START",
            {
                "input": user_input,
                "provider": getattr(self.llm, "provider_name", None),
                "model": self.llm.model_name,
            },
        )

        result = self.llm.generate(user_input)
        self._track_llm_metric(result)
        content = str(result.get("content", ""))

        logger.log_event(
            "CHATBOT_END",
            {
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", self.llm.model_name),
                "output": content,
            },
        )
        return content

    def _track_llm_metric(self, result: Dict[str, Any]) -> None:
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=result.get("model", self.llm.model_name),
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
