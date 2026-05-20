"""
Base LLM interface for VoicePilot-CLI.

Defines the abstract interface that all LLM backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional


class LLMBackendBase(ABC):
    """Abstract base class for LLM backends.

    All LLM backend implementations must inherit from this class
    and implement the required methods.

    Attributes:
        model: Name of the LLM model.
        temperature: Sampling temperature (0.0 - 2.0).
        max_tokens: Maximum tokens in response.
    """

    def __init__(
        self,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize the LLM backend.

        Args:
            model: Model name/identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a complete response for the given messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional generation parameters.

        Returns:
            Generated response text.
        """
        ...

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        """Stream a response for the given messages.

        Yields response text chunks as they are generated.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional generation parameters.

        Yields:
            Response text chunks.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available and ready to use.

        Returns:
            True if the backend is available.
        """
        ...

    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for the API.

        Default implementation passes messages through unchanged.
        Subclasses can override to add backend-specific formatting.

        Args:
            messages: List of message dicts.

        Returns:
            Formatted message list.
        """
        return messages

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration.

        Returns:
            Dictionary with model information.
        """
        return {
            "backend": self.__class__.__name__,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
