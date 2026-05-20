"""LLM module for VoicePilot-CLI.

Provides LLM backend interfaces and implementations for:
- OpenAI and compatible APIs
- Ollama local models
- GLM (ZhipuAI) API
"""

from voicepilot_cli.llm.base import LLMBackendBase

__all__ = ["LLMBackendBase"]
