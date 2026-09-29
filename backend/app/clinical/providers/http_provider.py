import json
from typing import Optional
import httpx
from app.clinical.providers.base import BaseLLMProvider, ProviderNotConfiguredError, LLMProviderError


class HttpLLMProvider(BaseLLMProvider):
    """
    HTTP-based LLM provider connecting to external AI endpoints (Gemini or OpenAI-compatible).
    Requires explicit API key in environment configuration.
    """

    def __init__(
        self,
        provider_name: str,
        api_key: Optional[str],
        model_name: str,
        base_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        self._provider_name = provider_name
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

        if not self._api_key:
            raise ProviderNotConfiguredError(
                f"LLM Provider '{provider_name}' requires an API key in GENAI_API_KEY environment variable."
            )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_structured_narrative(
        self, system_instruction: str, user_prompt: str
    ) -> str:
        # Standard HTTP JSON execution against configured endpoint
        url = self._base_url or (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model_name}:generateContent"
            if "gemini" in self._provider_name.lower()
            else "https://api.openai.com/v1/chat/completions"
        )

        headers = {
            "Content-Type": "application/json",
        }
        if "gemini" in self._provider_name.lower():
            headers["x-goog-api-key"] = self._api_key
            payload = {
                "contents": [{"parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }
        else:
            headers["Authorization"] = f"Bearer {self._api_key}"
            payload = {
                "model": self._model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if not resp.is_success:
                    raise LLMProviderError(
                        f"External LLM provider returned HTTP error {resp.status_code}: {resp.text[:200]}"
                    )
                res_json = resp.json()

                if "gemini" in self._provider_name.lower():
                    raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raw_text = res_json["choices"][0]["message"]["content"]
                return raw_text
        except httpx.RequestError as exc:
            raise LLMProviderError(f"HTTP request to LLM provider failed: {str(exc)}")
