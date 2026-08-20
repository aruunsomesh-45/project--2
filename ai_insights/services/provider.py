"""
Concrete AIProvider implementations, and a factory that picks one from
settings. Swap providers by changing AI_PROVIDER in .env — nothing else in
the app needs to know or care.
"""

import logging

from django.conf import settings

from .base import AIProvider, AIProviderError

logger = logging.getLogger('ai_insights')


class AnthropicProvider(AIProvider):
    """Default provider — calls the Anthropic Messages API."""

    def __init__(self, api_key, model):
        self._model = model
        try:
            import anthropic
        except ImportError as e:
            raise AIProviderError("anthropic package is not installed") from e
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def model_name(self):
        return self._model

    def generate(self, system_prompt, user_prompt):
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:  # noqa: BLE001 — any SDK/network failure becomes AIProviderError
            raise AIProviderError(f"Anthropic API call failed: {e.__class__.__name__}") from e

        text_parts = [block.text for block in response.content if getattr(block, 'type', None) == 'text']
        if not text_parts:
            raise AIProviderError("Anthropic response had no text content")
        return ''.join(text_parts)


class GeminiProvider(AIProvider):
    """Google Gemini via the google-genai SDK, using an AI Studio API key."""

    def __init__(self, api_key, model):
        self._model = model
        try:
            from google import genai
        except ImportError as e:
            raise AIProviderError("google-genai package is not installed") from e
        self._client = genai.Client(api_key=api_key)

    @property
    def model_name(self):
        return self._model

    def generate(self, system_prompt, user_prompt):
        try:
            from google.genai import types
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                # Gemini's JSON output for this schema runs more verbose than
                # Claude's — 2000 tokens truncated it mid-object in testing,
                # producing unparseable JSON. Give it more room.
                config=types.GenerateContentConfig(system_instruction=system_prompt, max_output_tokens=4096),
            )
        except Exception as e:  # noqa: BLE001 — any SDK/network failure becomes AIProviderError
            raise AIProviderError(f"Gemini API call failed: {e.__class__.__name__}") from e

        text = getattr(response, 'text', None)
        if not text:
            raise AIProviderError("Gemini response had no text content")
        return text


class NullProvider(AIProvider):
    """Used when no AI_API_KEY is configured. Every call fails cleanly with
    AIProviderError so the rest of the system falls back to the Phase 2
    deterministic profile — the app never breaks from a missing key."""

    @property
    def model_name(self):
        return 'none'

    def generate(self, system_prompt, user_prompt):
        raise AIProviderError("No AI provider configured (AI_API_KEY is empty)")


def get_provider():
    """Factory: returns the configured AIProvider instance."""
    if not settings.AI_API_KEY:
        return NullProvider()

    if settings.AI_PROVIDER == 'anthropic':
        try:
            return AnthropicProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
        except AIProviderError:
            logger.exception("Failed to initialize AnthropicProvider")
            return NullProvider()

    if settings.AI_PROVIDER == 'gemini':
        try:
            return GeminiProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
        except AIProviderError:
            logger.exception("Failed to initialize GeminiProvider")
            return NullProvider()

    logger.warning("Unknown AI_PROVIDER %r, falling back to NullProvider", settings.AI_PROVIDER)
    return NullProvider()
