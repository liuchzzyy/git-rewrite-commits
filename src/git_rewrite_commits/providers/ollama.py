"""Ollama local provider for commit message generation."""

import httpx

from .base import AIProvider


class OllamaProvider(AIProvider):
    """Ollama local provider for commit message generation."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Model to use (default: llama3.2)
            base_url: Ollama server URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Content-Type": "application/json"},
            timeout=120.0,  # Ollama can be slow
        )

    def _check_connection(self) -> None:
        """Check if Ollama is running and has the required model.

        Raises:
            ConnectionError: If cannot connect to Ollama
            ValueError: If model is not available
        """
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])
            model_names = [m["name"].split(":")[0] for m in models]

            model_base = self.model.split(":")[0]
            if model_base not in model_names:
                available = ", ".join(model_names) if model_names else "none"
                raise ValueError(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available models: {available}\n"
                    f"To pull the model, run: ollama pull {self.model}"
                )
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (run 'ollama serve' in terminal)"
            ) from e

    def generate_commit_message(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Generate a commit message using Ollama API.

        Args:
            prompt: The user prompt containing diff and context
            system_prompt: The system prompt defining behavior

        Returns:
            The generated commit message

        Raises:
            ConnectionError: If cannot connect to Ollama
            ValueError: If model not available or no message generated
            httpx.HTTPError: If the API request fails
        """
        self._check_connection()

        try:
            response = self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 200,
                    },
                },
            )
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {}).get("content", "").strip()

            if not message:
                raise ValueError("No commit message generated from Ollama")

            return message

        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (run 'ollama serve' in terminal)"
            ) from e

    def get_name(self) -> str:
        """Get the display name for this provider."""
        return f"Ollama ({self.model})"

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        if hasattr(self, "_client"):
            self._client.close()
