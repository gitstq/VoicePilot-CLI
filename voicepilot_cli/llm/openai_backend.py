"""
OpenAI (and compatible API) LLM backend for VoicePilot-CLI.

Supports OpenAI API and any compatible API (e.g., Azure OpenAI,
local LLM servers with OpenAI-compatible endpoints).
"""

from typing import Any, Dict, Generator, List, Optional

from voicepilot_cli.llm.base import LLMBackendBase
from voicepilot_cli.utils.logger import get_logger


class OpenAIBackend(LLMBackendBase):
    """OpenAI API backend.

    Connects to OpenAI's API or any compatible endpoint
    (e.g., local LLM servers, Azure OpenAI).

    Attributes:
        api_key: OpenAI API key.
        base_url: API base URL.
        organization: Optional organization ID.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        organization: str = "",
    ) -> None:
        """Initialize the OpenAI backend.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var).
            base_url: API base URL for OpenAI-compatible endpoints.
            model: Model name (e.g., 'gpt-3.5-turbo', 'gpt-4').
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
            organization: Optional organization ID.
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.logger = get_logger("llm.openai")

        # Try to get API key from environment if not provided
        import os
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.organization = organization

        self._client = None

    def _get_client(self):
        """Get or create the OpenAI client.

        Returns:
            OpenAI client instance.

        Raises:
            ImportError: If openai package is not installed.
        """
        if self._client is None:
            try:
                from openai import OpenAI
                client_kwargs: Dict[str, Any] = {
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                }
                if self.organization:
                    client_kwargs["organization"] = self.organization
                self._client = OpenAI(**client_kwargs)
            except ImportError:
                raise ImportError(
                    "openai package is required for OpenAI backend. "
                    "Install with: pip install openai"
                )
        return self._client

    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a complete response using OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters (temperature, max_tokens, etc.).

        Returns:
            Generated response text.

        Raises:
            Exception: If API call fails.
        """
        client = self._get_client()
        formatted = self.format_messages(messages)

        try:
            response = client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=formatted,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=False,
            )

            content = response.choices[0].message.content
            return content or ""

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        """Stream a response using OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters.

        Yields:
            Response text chunks.
        """
        client = self._get_client()
        formatted = self.format_messages(messages)

        try:
            stream = client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=formatted,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            yield f"[Error: {e}]"

    def is_available(self) -> bool:
        """Check if the OpenAI backend is available.

        Verifies that the openai package is installed and
        an API key is configured.

        Returns:
            True if available.
        """
        try:
            import openai  # noqa: F401
            if not self.api_key:
                self.logger.warning("OpenAI API key not configured")
                return False
            return True
        except ImportError:
            return False

    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for OpenAI API.

        Filters out empty messages and ensures proper format.

        Args:
            messages: Raw message list.

        Returns:
            Formatted message list.
        """
        formatted = []
        for msg in messages:
            if msg.get("content", "").strip():
                formatted.append({
                    "role": msg.get("role", "user"),
                    "content": msg["content"],
                })
        return formatted

    def list_models(self) -> List[str]:
        """List available models from the API.

        Returns:
            List of model name strings.
        """
        try:
            client = self._get_client()
            models = client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []
