import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.telemetry import metrics as metrics_module
from src.telemetry.metrics import PerformanceTracker


def test_llm_metric_contains_provider_model_tokens_and_latency(monkeypatch):
    events = []
    monkeypatch.setattr(metrics_module.logger, "log_event", lambda event, data: events.append((event, data)))
    tracker = PerformanceTracker()

    tracker.track_request(
        provider="mimo",
        model="mimo-v2.5-pro",
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        latency_ms=123,
    )

    assert len(events) == 1
    event_name, payload = events[0]
    assert event_name == "LLM_METRIC"
    assert payload["provider"] == "mimo"
    assert payload["model"] == "mimo-v2.5-pro"
    assert payload["prompt_tokens"] == 10
    assert payload["completion_tokens"] == 5
    assert payload["total_tokens"] == 15
    assert payload["latency_ms"] == 123
    assert payload["cost_estimate"] is None
    assert payload["cost_note"] == "N/A: token-plan quota"


def test_mimo_is_not_logged_as_openai(monkeypatch):
    events = []
    monkeypatch.setattr(metrics_module.logger, "log_event", lambda event, data: events.append((event, data)))
    tracker = PerformanceTracker()

    tracker.track_request(
        provider="mimo",
        model="mimo-v2.5-pro",
        usage={},
        latency_ms=0,
    )

    assert events[0][1]["provider"] == "mimo"
    assert events[0][1]["provider"] != "openai"


def test_api_key_is_not_logged(monkeypatch):
    secret = "fake-secret-key-for-test"
    monkeypatch.setenv("MIMO_API_KEY", secret)
    events = []
    monkeypatch.setattr(metrics_module.logger, "log_event", lambda event, data: events.append((event, data)))
    tracker = PerformanceTracker()

    tracker.track_request(
        provider="mimo",
        model="mimo-v2.5-pro",
        usage={"total_tokens": 1},
        latency_ms=1,
    )

    serialized = json.dumps(events)
    assert secret not in serialized
