import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.chatbot as chatbot_module
from src.chatbot import Chatbot
from src.core.llm_provider import LLMProvider


class FakeProvider(LLMProvider):
    def __init__(self):
        super().__init__(model_name="fake-model", api_key="fake-key")
        self.generate_calls = []

    def generate(self, prompt, system_prompt=None):
        self.generate_calls.append((prompt, system_prompt))
        return {
            "content": "fake answer",
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 2,
                "total_tokens": 7,
            },
            "latency_ms": 12,
            "provider": "fake",
            "model": self.model_name,
        }

    def stream(self, prompt, system_prompt=None):
        yield "fake answer"


def test_chatbot_calls_llm_exactly_once(monkeypatch):
    provider = FakeProvider()
    tracked = []
    events = []
    monkeypatch.setattr(chatbot_module.tracker, "track_request", lambda **kwargs: tracked.append(kwargs))
    monkeypatch.setattr(chatbot_module.logger, "log_event", lambda event, data: events.append((event, data)))

    result = Chatbot(provider).run("What products do you sell?")

    assert result == "fake answer"
    assert provider.generate_calls == [("What products do you sell?", None)]
    assert tracked == [
        {
            "provider": "fake",
            "model": "fake-model",
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 2,
                "total_tokens": 7,
            },
            "latency_ms": 12,
        }
    ]
    assert [event for event, _ in events] == ["CHATBOT_START", "CHATBOT_END"]


def test_chatbot_does_not_call_tools(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(chatbot_module.tracker, "track_request", lambda **kwargs: None)
    monkeypatch.setattr(chatbot_module.logger, "log_event", lambda event, data: None)

    Chatbot(provider).run("I want to buy 2 iPhones with WINNER.")

    assert len(provider.generate_calls) == 1
