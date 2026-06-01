import os
from typing import Optional

from dotenv import load_dotenv

from src.core.llm_provider import LLMProvider


class ProviderConfigError(ValueError):
    """Raised when provider configuration is missing or invalid."""


def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Create an LLM provider from CLI override or environment configuration."""
    load_dotenv()
    provider = _normalize_provider_name(provider_name or os.getenv("DEFAULT_PROVIDER") or "mimo")

    if provider == "mimo":
        api_key = _require_env("MIMO_API_KEY", "Missing MIMO_API_KEY in .env")
        model = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
        base_url = os.getenv("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
        from src.core.mimo_provider import MiMoProvider

        return MiMoProvider(model_name=model, api_key=api_key, base_url=base_url)

    if provider == "gemini":
        api_key = _require_env("GEMINI_API_KEY", "Missing GEMINI_API_KEY in .env")
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(model_name=model, api_key=api_key)

    if provider == "openai":
        api_key = _require_env("OPENAI_API_KEY", "Missing OPENAI_API_KEY in .env")
        model = os.getenv("OPENAI_MODEL", os.getenv("DEFAULT_MODEL", "gpt-4o"))
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name=model, api_key=api_key)

    if provider == "local":
        model_path = _require_env("LOCAL_MODEL_PATH", "Missing LOCAL_MODEL_PATH in .env")
        from src.core.local_provider import LocalProvider

        return LocalProvider(model_path=model_path)

    raise ProviderConfigError(
        f"Unsupported provider '{provider}'. Supported providers: mimo, gemini, openai, local."
    )


def _normalize_provider_name(provider_name: str) -> str:
    normalized = provider_name.strip().lower()
    aliases = {
        "google": "gemini",
    }
    return aliases.get(normalized, normalized)


def _require_env(name: str, message: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ProviderConfigError(message)
    return value
