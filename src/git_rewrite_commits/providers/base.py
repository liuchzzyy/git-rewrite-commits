"""Base protocol and types for AI providers."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    model: str
    temperature: float = 0.3
    max_tokens: int = 200


@dataclass
class GeneratedMessage:
    """Result from AI message generation."""

    content: str
    model: str
    tokens_used: int = 0


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def generate_commit_message(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Generate a commit message from a prompt.

        Args:
            prompt: The user prompt containing diff and context
            system_prompt: The system prompt defining behavior

        Returns:
            The generated commit message
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the display name for this provider."""
        ...


class OpenAICompatibleProvider(AIProvider):
    """Base class for OpenAI-compatible API providers.

    This base class handles the common logic for providers that use
    OpenAI-compatible chat completions API (OpenAI, DeepSeek, etc.).

    Subclasses only need to define:
        - BASE_URL: The API base URL
        - ENV_VAR_NAME: Environment variable name for API key
        - DEFAULT_MODEL: Default model name
        - PROVIDER_NAME: Display name for the provider
    """

    BASE_URL: str
    ENV_VAR_NAME: str
    DEFAULT_MODEL: str
    PROVIDER_NAME: str

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            api_key: API key (defaults to environment variable)
            model: Model to use (defaults to DEFAULT_MODEL)

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.environ.get(self.ENV_VAR_NAME)
        if not self.api_key:
            raise ValueError(
                f"{self.PROVIDER_NAME} API key is required. "
                f"Set {self.ENV_VAR_NAME} environment variable or pass it as an option."
            )
        self.model = model or self.DEFAULT_MODEL
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=60.0,
        )

    def generate_commit_message(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Generate a commit message using the API.

        Args:
            prompt: The user prompt containing diff and context
            system_prompt: The system prompt defining behavior

        Returns:
            The generated commit message

        Raises:
            httpx.HTTPError: If the API request fails
        """
        response = self._client.post(
            "chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            },
        )
        response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]["content"].strip()

        if not message:
            raise ValueError(f"No commit message generated from {self.PROVIDER_NAME}")

        return message

    def get_name(self) -> str:
        """Get the display name for this provider."""
        return f"{self.PROVIDER_NAME} ({self.model})"

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        if hasattr(self, "_client"):
            self._client.close()
