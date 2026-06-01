import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import agent as agent_module
from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, outputs):
        super().__init__(model_name="fake-model", api_key="fake-key")
        self.outputs = list(outputs)
        self.generate_calls = []

    def generate(self, prompt, system_prompt=None):
        self.generate_calls.append((prompt, system_prompt))
        content = self.outputs.pop(0) if self.outputs else "Final Answer: done"
        return {
            "content": content,
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "latency_ms": 9,
            "provider": "fake",
            "model": self.model_name,
        }

    def stream(self, prompt, system_prompt=None):
        yield "fake"


def capture_telemetry(monkeypatch):
    events = []
    metrics = []
    monkeypatch.setattr(agent_module.logger, "log_event", lambda event, data: events.append((event, data)))
    monkeypatch.setattr(agent_module.tracker, "track_request", lambda **kwargs: metrics.append(kwargs))
    return events, metrics


def make_lookup_tool(calls):
    def lookup(item_name):
        calls.append(item_name)
        return {
            "status": "success",
            "data": {"item_name": item_name, "available": True},
            "error": None,
        }

    return {
        "name": "lookup",
        "description": "Look up a product.",
        "function": lookup,
        "input_schema": {"item_name": "required string"},
    }


def make_discount_tool(calls):
    def discount(coupon_code):
        calls.append(coupon_code)
        return {
            "status": "success",
            "data": {"coupon_code": coupon_code, "discount_percent": 10},
            "error": None,
        }

    return {
        "name": "discount",
        "description": "Look up a coupon.",
        "function": discount,
        "input_schema": {"coupon_code": "required string"},
    }


def test_agent_v1_returns_direct_final_answer(monkeypatch):
    events, metrics = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(["Thought: I can answer.\nFinal Answer: hello"])

    result = ReActAgent(provider, [], max_steps=3).run("Say hello")

    assert result == "hello"
    assert len(provider.generate_calls) == 1
    assert len(metrics) == 1
    assert [event for event, _ in events] == [
        "AGENT_START",
        "AGENT_STEP",
        "FINAL_ANSWER",
        "AGENT_END",
    ]


def test_agent_v1_executes_valid_action_and_feeds_observation(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        [
            'Thought: I need data.\nAction: lookup({"item_name": "iPhone 15"})',
            "Thought: I have the observation.\nFinal Answer: iPhone 15 is available.",
        ]
    )

    result = ReActAgent(provider, [make_lookup_tool(calls)], max_steps=3).run("Check iPhone 15")

    assert result == "iPhone 15 is available."
    assert calls == ["iPhone 15"]
    assert len(provider.generate_calls) == 2
    next_prompt = provider.generate_calls[1][0]
    assert "Observation:" in next_prompt
    assert "iPhone 15" in next_prompt
    assert "TOOL_CALL" in [event for event, _ in events]
    assert "TOOL_RESULT" in [event for event, _ in events]


def test_agent_v1_executes_action_before_final_answer_in_same_output(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        [
            (
                'Thought: I need data.\n'
                'Action: lookup({"item_name": "iPhone 15"})\n'
                'Observation: made-up observation\n'
                'Final Answer: made-up final'
            ),
            "Thought: Now I can answer from the real observation.\nFinal Answer: real final",
        ]
    )

    result = ReActAgent(provider, [make_lookup_tool(calls)], max_steps=3).run("Check iPhone 15")

    assert result == "real final"
    assert calls == ["iPhone 15"]
    assert len(provider.generate_calls) == 2
    assert "made-up final" not in provider.generate_calls[1][0]
    assert [event for event, _ in events].count("TOOL_CALL") == 1


def test_agent_v1_executes_multiple_actions_from_one_output(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    lookup_calls = []
    discount_calls = []
    provider = ScriptedProvider(
        [
            (
                'Thought: I need two tools.\n'
                'Action: lookup({"item_name": "iPhone 15"})\n'
                'Observation: model-written observation\n'
                'Action: discount({"coupon_code": "WINNER"})'
            ),
            "Thought: I have both real observations.\nFinal Answer: done",
        ]
    )
    tools = [make_lookup_tool(lookup_calls), make_discount_tool(discount_calls)]

    result = ReActAgent(provider, tools, max_steps=3).run("Check order")

    assert result == "done"
    assert lookup_calls == ["iPhone 15"]
    assert discount_calls == ["WINNER"]
    next_prompt = provider.generate_calls[1][0]
    assert '"tool_name": "lookup"' in next_prompt
    assert '"tool_name": "discount"' in next_prompt
    assert "model-written observation" not in next_prompt
    assert [event for event, _ in events].count("TOOL_CALL") == 2


def test_agent_v1_unknown_tool_becomes_observation(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            'Thought: I need a nonexistent tool.\nAction: made_up({"x": 1})',
            "Thought: The tool failed.\nFinal Answer: I cannot use that tool.",
        ]
    )

    result = ReActAgent(provider, [], max_steps=3).run("Use a made-up tool")

    assert result == "I cannot use that tool."
    assert "UNKNOWN_TOOL" in provider.generate_calls[1][0]
    assert "UNKNOWN_TOOL" in [event for event, _ in events]


def test_agent_v1_stops_at_max_steps(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    calls = []
    provider = ScriptedProvider(
        ['Thought: I will keep calling.\nAction: lookup({"item_name": "iPhone 15"})']
    )

    result = ReActAgent(provider, [make_lookup_tool(calls)], max_steps=1).run("Loop")

    assert result == "I could not complete the request within the allowed steps."
    assert calls == ["iPhone 15"]
    assert [event for event, _ in events][-2:] == ["MAX_STEPS_EXCEEDED", "AGENT_END"]


def test_agent_v1_parser_error_is_fed_back(monkeypatch):
    events, _ = capture_telemetry(monkeypatch)
    provider = ScriptedProvider(
        [
            "Thought: I forgot the required format.",
            "Thought: I recovered.\nFinal Answer: recovered",
        ]
    )

    result = ReActAgent(provider, [], max_steps=3).run("Recover")

    assert result == "recovered"
    assert "PARSER_ERROR" in provider.generate_calls[1][0]
    assert "PARSER_ERROR" in [event for event, _ in events]
