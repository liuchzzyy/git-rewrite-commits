"""DeepSeek API provider for commit message generation."""

from .base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider for commit message generation.

    DeepSeek API is OpenAI-compatible, making integration straightforward.
    Supports models: deepseek-chat (default), deepseek-coder, deepseek-reasoner
    """

    BASE_URL = "https://api.deepseek.com/"
    ENV_VAR_NAME = "DEEPSEEK_API_KEY"
    DEFAULT_MODEL = "deepseek-chat"
    PROVIDER_NAME = "DeepSeek"
