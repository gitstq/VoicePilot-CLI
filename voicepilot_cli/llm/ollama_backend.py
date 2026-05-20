"""
Ollama local model LLM backend for VoicePilot-CLI.

Connects to a locally running Ollama server to use open-source
models like LLaMA, Mistral, etc.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Generator, List, Optional

from voicepilot_cli.llm.base import LLMBackendBase
from voicepilot_cli.utils.logger import get_logger


class OllamaBackend(LLMBackendBase):
    """Ollama local model backend.

    Connects to a locally running Ollama server via its HTTP API.
    Supports all models available through Ollama.

    Attributes:
        base_url: Ollama server base URL.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize the Ollama backend.

        Args:
            base_url: Ollama server URL (default: http://localhost:11434).
            model: Model name (e.g., 'llama3', 'mistral', 'codellama').
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.logger = get_logger("llm.ollama")
        self.base_url = base_url.rstrip("/")

    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a complete response using Ollama API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters.

        Returns:
            Generated response text.

        Raises:
            Exception: If API call fails.
        """
        url = f"{self.base_url}/api/chat"
        formatted = self.format_messages(messages)

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": formatted,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")

        except urllib.error.URLError as e:
            self.logger.error(f"Cannot connect to Ollama server at {self.base_url}: {e}")
            raise ConnectionError(
                f"Cannot connect to Ollama server at {self.base_url}. "
                "Make sure Ollama is running. Install from: https://ollama.ai"
            )
        except Exception as e:
            self.logger.error(f"Ollama API error: {e}")
            raise

    def stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        """Stream a response using Ollama API.

        Uses the streaming endpoint to yield response chunks.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters.

        Yields:
            Response text chunks.
        """
        url = f"{self.base_url}/api/chat"
        formatted = self.format_messages(messages)

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": formatted,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                buffer = ""
                while True:
                    chunk = response.read(1)
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8")

                    # Process complete JSON lines (NDJSON format)
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            result = json.loads(line)
                            content = result.get("message", {}).get("content", "")
                            if content:
                                yield content

                            # Check if done
                            if result.get("done", False):
                                return
                        except json.JSONDecodeError:
                            continue

        except urllib.error.URLError as e:
            self.logger.error(f"Cannot connect to Ollama: {e}")
            yield f"[Error: Cannot connect to Ollama at {self.base_url}]"
        except Exception as e:
            self.logger.error(f"Ollama streaming error: {e}")
            yield f"[Error: {e}]"

    def is_available(self) -> bool:
        """Check if the Ollama server is available.

        Pings the Ollama server to verify connectivity.

        Returns:
            True if Ollama server is reachable.
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available models from the Ollama server.

        Returns:
            List of model name strings.
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return [m.get("name", "") for m in result.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to list Ollama models: {e}")
            return []

    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model from the Ollama registry.

        Args:
            model_name: Name of the model to pull.

        Returns:
            True if successful.
        """
        try:
            url = f"{self.base_url}/api/pull"
            payload = {"name": model_name, "stream": False}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=600) as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Failed to pull model '{model_name}': {e}")
            return False

    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for Ollama API.

        Ollama uses the same message format as OpenAI.

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
