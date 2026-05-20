"""
GLM (ZhipuAI) LLM backend for VoicePilot-CLI.

Connects to ZhipuAI's API for GLM series models (GLM-4, GLM-3-Turbo, etc.).
"""

import json
import os
from typing import Any, Dict, Generator, List, Optional

from voicepilot_cli.llm.base import LLMBackendBase
from voicepilot_cli.utils.logger import get_logger


class GLMBackend(LLMBackendBase):
    """GLM (ZhipuAI) API backend.

    Connects to ZhipuAI's API for GLM series models.
    GLM models are particularly good for Chinese language tasks.

    Attributes:
        api_key: ZhipuAI API key.
    """

    # ZhipuAI API base URL
    API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(
        self,
        api_key: str = "",
        model: str = "glm-4",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize the GLM backend.

        Args:
            api_key: ZhipuAI API key (or set ZHIPUAI_API_KEY env var).
            model: Model name (e.g., 'glm-4', 'glm-3-turbo', 'glm-4-flash').
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.logger = get_logger("llm.glm")

        # Try to get API key from environment if not provided
        self.api_key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")

        self._client = None

    def _get_client(self):
        """Get or create the ZhipuAI client.

        Returns:
            ZhipuAI client instance.

        Raises:
            ImportError: If zhipuai package is not installed.
        """
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "zhipuai package is required for GLM backend. "
                    "Install with: pip install zhipuai"
                )
        return self._client

    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a complete response using ZhipuAI API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters.

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
            self.logger.error(f"GLM API error: {e}")
            raise

    def stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        """Stream a response using ZhipuAI API.

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
            self.logger.error(f"GLM streaming error: {e}")
            yield f"[Error: {e}]"

    def is_available(self) -> bool:
        """Check if the GLM backend is available.

        Verifies that the zhipuai package is installed and
        an API key is configured.

        Returns:
            True if available.
        """
        try:
            import zhipuai  # noqa: F401
            if not self.api_key:
                self.logger.warning("ZhipuAI API key not configured")
                return False
            return True
        except ImportError:
            return False

    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for ZhipuAI API.

        GLM uses the same message format as OpenAI.

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
        """List available GLM models.

        Returns:
            List of supported model names.
        """
        return [
            "glm-4-plus",
            "glm-4-0520",
            "glm-4",
            "glm-4-air",
            "glm-4-airx",
            "glm-4-long",
            "glm-4-flashx",
            "glm-4-flash",
            "glm-3-turbo",
        ]
