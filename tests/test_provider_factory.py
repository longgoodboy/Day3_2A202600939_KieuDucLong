import os
import sys
from types import SimpleNamespace

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import provider_factory
from src.core.mimo_provider import MiMoProvider
from src.core.provider_factory import ProviderConfigError, create_provider


class FakeOpenAI:
    calls = []

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="MiMo response"),
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=3,
                completion_tokens=4,
                total_tokens=7,
            ),
        )


class FakeOpenAIWithoutUsage(FakeOpenAI):
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="MiMo response"),
                )
            ],
            usage=None,
        )


@pytest.fixture(autouse=True)
def clean_provider_env(monkeypatch):
    for key in [
        "DEFAULT_PROVIDER",
        "MIMO_API_KEY",
        "MIMO_BASE_URL",
        "MIMO_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "LOCAL_MODEL_PATH",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(provider_factory, "load_dotenv", lambda: None)


def test_create_provider_defaults_to_mimo_and_requires_key():
    with pytest.raises(ProviderConfigError, match="Missing MIMO_API_KEY in .env"):
        create_provider()


@pytest.mark.parametrize(
    ("provider_name", "expected_error"),
    [
        ("mimo", "Missing MIMO_API_KEY in .env"),
        ("gemini", "Missing GEMINI_API_KEY in .env"),
        ("google", "Missing GEMINI_API_KEY in .env"),
        ("openai", "Missing OPENAI_API_KEY in .env"),
    ],
)
def test_create_provider_reports_clear_missing_key_errors(provider_name, expected_error):
    with pytest.raises(ProviderConfigError, match=expected_error):
        create_provider(provider_name)


def test_create_provider_rejects_unknown_provider():
    with pytest.raises(ProviderConfigError, match="Unsupported provider 'unknown'"):
        create_provider("unknown")


def test_create_provider_builds_mimo_from_environment(monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "test-mimo-key")
    monkeypatch.setenv("MIMO_MODEL", "mimo-test-model")
    monkeypatch.setenv("MIMO_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr("src.core.mimo_provider.OpenAI", FakeOpenAI)

    provider = create_provider("mimo")

    assert isinstance(provider, MiMoProvider)
    assert provider.api_key == "test-mimo-key"
    assert provider.model_name == "mimo-test-model"
    assert provider.base_url == "https://example.test/v1"


def test_mimo_provider_generate_returns_standard_shape(monkeypatch):
    FakeOpenAI.calls = []
    monkeypatch.setattr("src.core.mimo_provider.OpenAI", FakeOpenAI)
    provider = MiMoProvider(
        model_name="mimo-test-model",
        api_key="test-mimo-key",
        base_url="https://example.test/v1",
    )

    result = provider.generate("hello", system_prompt="be concise")

    assert result["content"] == "MiMo response"
    assert result["provider"] == "mimo"
    assert result["model"] == "mimo-test-model"
    assert result["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }
    assert isinstance(result["latency_ms"], int)
    assert FakeOpenAI.calls[0]["messages"] == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "hello"},
    ]


def test_mimo_provider_uses_safe_usage_defaults(monkeypatch):
    monkeypatch.setattr("src.core.mimo_provider.OpenAI", FakeOpenAIWithoutUsage)
    provider = MiMoProvider(
        model_name="mimo-test-model",
        api_key="test-mimo-key",
        base_url="https://example.test/v1",
    )

    result = provider.generate("hello")

    assert result["usage"] == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
