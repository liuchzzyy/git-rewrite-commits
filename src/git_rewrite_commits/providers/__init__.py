"""AI Provider implementations for commit message generation."""

from .base import AIProvider, ProviderConfig
from .openai import OpenAIProvider
from .ollama import OllamaProvider
from .deepseek import DeepSeekProvider

__all__ = [
    "AIProvider",
    "ProviderConfig",
    "OpenAIProvider",
    "OllamaProvider",
    "DeepSeekProvider",
    "create_provider",
]


def create_provider(
    provider: str = "openai",
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> AIProvider:
    """Factory function to create an AI provider instance.

    Args:
        provider: Provider name - 'openai', 'ollama', or 'deepseek'
        api_key: API key for the provider (required for openai/deepseek)
        model: Model name to use (provider-specific defaults if not set)
        base_url: Base URL for the API (used for ollama, optional for others)

    Returns:
        An AIProvider instance

    Raises:
        ValueError: If provider is unknown or required config is missing
    """
    provider = provider.lower()

    if provider == "ollama":
        return OllamaProvider(
            model=model or "llama3.2",
            base_url=base_url or "http://localhost:11434",
        )
    elif provider == "deepseek":
        return DeepSeekProvider(
            api_key=api_key,
            model=model or "deepseek-chat",
        )
    elif provider == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4o-mini",
        )
    else:
        raise ValueError(
            f"Unknown provider: {provider}. Supported providers: openai, ollama, deepseek"
        )
