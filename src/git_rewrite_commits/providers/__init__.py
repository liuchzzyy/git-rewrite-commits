"""AI Provider implementations for commit message generation."""

from .base import AIProvider, OpenAICompatibleProvider, ProviderConfig
from .deepseek import DeepSeekProvider
from .openai import OpenAIProvider

__all__ = [
    "AIProvider",
    "ProviderConfig",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
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
        provider: Provider name - 'openai' or 'deepseek'
        api_key: API key for the provider (required for openai/deepseek)
        model: Model name to use (provider-specific defaults if not set)
        base_url: Base URL for the API (optional)

    Returns:
        An AIProvider instance

    Raises:
        ValueError: If provider is unknown or required config is missing
    """
    provider = provider.lower()

    if provider == "deepseek":
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
        raise ValueError(f"Unknown provider: {provider}. Supported providers: openai, deepseek")
