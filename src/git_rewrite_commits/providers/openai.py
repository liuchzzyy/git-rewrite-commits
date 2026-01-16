"""OpenAI API provider for commit message generation."""

from .base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider for commit message generation.

    Uses the OpenAI Chat Completions API.
    Supports models: gpt-4o-mini (default), gpt-4o, gpt-3.5-turbo
    """

    BASE_URL = "https://api.openai.com/v1/"
    ENV_VAR_NAME = "OPENAI_API_KEY"
    DEFAULT_MODEL = "gpt-4o-mini"
    PROVIDER_NAME = "OpenAI"
