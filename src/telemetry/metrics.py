from typing import Any, Dict, List, Optional
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        cost_estimate, cost_note = self._calculate_cost(provider, model, usage)
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate,
            "cost_note": cost_note,
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(
        self,
        provider: str,
        model: str,
        usage: Dict[str, int],
    ) -> tuple[Optional[float], Optional[str]]:
        """
        Return a conservative cost estimate.

        MiMo Token Plan pricing is quota-based in this lab context, so avoid
        reporting 0.0 as if monetary cost were known to be free.
        """
        if provider == "mimo" or model == "mimo-v2.5-pro":
            return None, "N/A: token-plan quota"
        return (usage.get("total_tokens", 0) / 1000) * 0.01, "mock estimate"

# Global tracker instance
tracker = PerformanceTracker()
