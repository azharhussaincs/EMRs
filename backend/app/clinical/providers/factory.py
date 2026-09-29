from typing import Optional
from app.core.config import settings
from app.clinical.providers.base import BaseLLMProvider, ProviderNotConfiguredError
from app.clinical.providers.mock import MockLLMProvider
from app.clinical.providers.http_provider import HttpLLMProvider


def get_llm_provider(
    provider_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory function returning the configured BaseLLMProvider instance.
    Enforces strict configuration checks.
    """
    provider_name = (provider_override or settings.GENAI_PROVIDER).lower()
    api_key = api_key_override if api_key_override is not None else settings.GENAI_API_KEY

    if provider_name == "mock":
        return MockLLMProvider(model_name=settings.GENAI_MODEL_NAME)

    if provider_name in ("gemini", "openai"):
        if not api_key:
            raise ProviderNotConfiguredError(
                f"LLM Provider '{provider_name}' is selected, but GENAI_API_KEY is not configured in the environment."
            )
        return HttpLLMProvider(
            provider_name=provider_name,
            api_key=api_key,
            model_name=settings.GENAI_MODEL_NAME,
            base_url=settings.GENAI_API_BASE_URL,
            timeout_seconds=settings.GENAI_TIMEOUT_SECONDS,
        )

    raise ProviderNotConfiguredError(
        f"Unsupported or unrecognized LLM provider '{provider_name}'. Supported: 'mock', 'gemini', 'openai'."
    )
