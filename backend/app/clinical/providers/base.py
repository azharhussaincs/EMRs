from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class ProviderNotConfiguredError(LLMProviderError):
    """Raised when provider API key or required configuration is missing."""
    pass


class BaseLLMProvider(ABC):
    """
    Abstract interface for swappable LLM narrative generators.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of provider (e.g. 'mock', 'gemini', 'openai')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass

    @abstractmethod
    async def generate_structured_narrative(
        self, system_instruction: str, user_prompt: str
    ) -> str:
        """
        Executes request against provider and returns raw JSON text string.
        """
        pass
