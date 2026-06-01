import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures"))

from src.agent import agent_v2 as agent_v2_module
from src.agent.agent_v2 import ReActAgentV2
from src.core.llm_provider import LLMProvider
import llm_outputs


class ScriptedProvider(LLMProvider):
    def __init__(self, outputs):
        super().__init__(model_name="fake-model", api_key="fake-key")
        self.outputs = list(outputs)
        self.generate_calls = []

    def generate(self, prompt, system_prompt=None):
        self.generate_calls.append((prompt, system_prompt))
        output = self.outputs.pop(0) if self.outputs else "Final Answer: done"
        if isinstance(output, Exception):
            raise output
        return {
            "content": output,
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 6,
                "total_tokens": 17,
            },
            "latency_ms": 10,
            "provider": "fake",
            "model": self.model_name,
        }

    def stream(self, prompt, system_prompt=None):
        yield "fake"


def capture_telemetry(monkeypatch):
    events = []
    metrics = []
    monkeypatch.setattr(agent_v2_module.logger, "log_event", lambda event, data: events.append((event, data)))
    monkeypatch.setattr(agent_v2_module.tracker, "track_request", lambda **kwargs: metrics.append(kwargs))
    return events, metrics


def make_lookup_tool(calls):
    def lookup(item_name):
        calls.append(item_name)
        return {
            "status": "success",
            "data": {"item_name": item_name, "price_vnd": 20000000},
            "error": None,
        }

    return {
        "name": "lookup",
        "description": "Look up a product.",
        "function": lookup,
        "input_schema": {"item_name": "required string"},
    }


def test_agent_v2_parses_markdown_fenced_json_and_executes_tool(monkeypatch):
    events, metrics = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        [
            llm_outputs.MARKDOWN_FENCED_ACTION,
            "Final Answer: iPhone 15 costs 20,000,000 VND.",
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool(calls)], max_steps=3).run("Price?")

    assert result == "iPhone 15 costs 20,000,000 VND."
    assert calls == ["iPhone 15"]
    assert "TOOL_CALL" in [event for event, _ in events]
    assert len(metrics) == 2


def test_agent_v2_retries_model_written_observation(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        [
            llm_outputs.MODEL_WRITTEN_OBSERVATION,
            'Action: lookup({"item_name": "iPhone 15"})',
            "Final Answer: real answer from tool.",
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool(calls)], max_steps=3).run("Check iPhone")

    assert result == "real answer from tool."
    assert calls == ["iPhone 15"]
    event_names = [event for event, _ in events]
    assert "PARSER_ERROR" in event_names
    assert "RETRY" in event_names
    assert "TOOL_CALL" in event_names


def test_agent_v2_handles_unknown_tool_without_crashing(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            llm_outputs.UNKNOWN_TOOL_ACTION,
            "Final Answer: I cannot use that tool.",
        ]
    )

    result = ReActAgentV2(provider, [], max_steps=3).run("Use unknown")

    assert result == "I cannot use that tool."
    event_names = [event for event, _ in events]
    assert "UNKNOWN_TOOL" in event_names
    assert "AGENT_END" in event_names
    assert "UNKNOWN_TOOL" in provider.generate_calls[1][0]


def test_agent_v2_rejects_wrong_argument_type(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            llm_outputs.WRONG_ARGUMENT_TYPE,
            "Final Answer: The argument type was invalid.",
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool([])], max_steps=3).run("Bad args")

    assert result == "The argument type was invalid."
    assert "INVALID_ARGUMENTS" in [event for event, _ in events]
    assert "INVALID_ARGUMENT_TYPE" in provider.generate_calls[1][0]


def test_agent_v2_rejects_missing_argument(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            llm_outputs.MISSING_ARGUMENT,
            "Final Answer: item_name is required.",
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool([])], max_steps=3).run("Missing arg")

    assert result == "item_name is required."
    assert "INVALID_ARGUMENTS" in [event for event, _ in events]
    assert "MISSING_ARGUMENT" in provider.generate_calls[1][0]


def test_agent_v2_stops_repeated_action(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            llm_outputs.REPEATED_ACTION,
            llm_outputs.REPEATED_ACTION,
            llm_outputs.REPEATED_ACTION,
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool([])], max_steps=5).run("Loop")

    assert result == "I stopped because the same tool action repeated too many times without progress."
    assert "REPEATED_ACTION" in [event for event, _ in events]
    assert events[-1][0] == "AGENT_END"
    assert events[-1][1]["termination_reason"] == "repeated_action"


def test_agent_v2_reuses_cached_observation_once_before_stopping(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        [
            llm_outputs.REPEATED_ACTION,
            llm_outputs.REPEATED_ACTION,
            "Final Answer: I used the cached observation.",
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool(calls)], max_steps=5).run("Loop once")

    assert result == "I used the cached observation."
    assert calls == ["iPhone 15"]
    event_names = [event for event, _ in events]
    assert "REPEATED_ACTION" in event_names
    assert events[-1][0] == "AGENT_END"
    assert events[-1][1]["termination_reason"] == "final_answer"
    assert "cached_observation" in provider.generate_calls[2][0]


def test_agent_v2_handles_provider_error_with_retry_and_graceful_end(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            RuntimeError("429 Too many requests"),
            RuntimeError("429 Too many requests"),
            RuntimeError("429 Too many requests"),
        ]
    )

    result = ReActAgentV2(provider, [make_lookup_tool([])], max_steps=3, max_retries=2).run("Rate limit")

    assert "provider is unavailable or rate-limited" in result
    event_names = [event for event, _ in events]
    assert event_names.count("PROVIDER_ERROR") == 3
    assert event_names.count("RETRY") == 2
    assert events[-1][0] == "AGENT_END"
    assert events[-1][1]["termination_reason"] == "provider_error"
