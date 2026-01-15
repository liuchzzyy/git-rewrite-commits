"""Base protocol and types for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
