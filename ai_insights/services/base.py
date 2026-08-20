"""
AI provider abstraction. The rest of the app talks to `AIProvider` only —
never to a specific SDK — so the provider can be swapped without touching
any Django views, models, or templates.
"""

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised when the provider fails to produce a response (timeout, API
    error, missing credentials, etc.). Callers must treat this as
    'AI unavailable', never let it propagate to a 500."""


class AIProvider(ABC):
    """A provider takes a system prompt + user prompt and returns raw text.
    Parsing/validating that text into structured insights happens above
    this layer (student_insights.py + validators.py), so a provider
    implementation stays as thin as possible."""

    @abstractmethod
    def generate(self, system_prompt, user_prompt):
        """Return the raw text response from the model. Raise
        AIProviderError on any failure (network, auth, timeout, etc.)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self):
        raise NotImplementedError
