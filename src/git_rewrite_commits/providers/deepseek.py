"""DeepSeek API provider for commit message generation."""

import os

import httpx

from .base import AIProvider


class DeepSeekProvider(AIProvider):
    """DeepSeek API provider for commit message generation.

    DeepSeek API is OpenAI-compatible, making integration straightforward.
    Supports models: deepseek-chat, deepseek-coder, deepseek-reasoner
    """

    BASE_URL = "https://api.deepseek.com/"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-chat",
    ) -> None:
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
            model: Model to use (default: deepseek-chat)
                   Available: deepseek-chat, deepseek-coder, deepseek-reasoner

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key is required. "
                "Set DEEPSEEK_API_KEY environment variable or pass it as an option."
            )
        self.model = model
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
        """Generate a commit message using DeepSeek API.

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
            raise ValueError("No commit message generated from DeepSeek")

        return message

    def get_name(self) -> str:
        """Get the display name for this provider."""
        return f"DeepSeek ({self.model})"

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        if hasattr(self, "_client"):
            self._client.close()
