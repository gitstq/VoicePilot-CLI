"""
Configuration management for VoicePilot-CLI.

Handles loading, saving, and accessing configuration from YAML files.
Configuration is stored at ~/.voicepilot/config.yaml with sensible defaults.
Uses only Python stdlib (no PyYAML dependency) - implements a minimal YAML-like
parser for simple nested structures.
"""

import json
import os
import copy
from pathlib import Path
from typing import Any, Dict, Optional, Union


# ─── Default Configuration ───────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "llm": {
        "backend": "ollama",
        "model": "llama3",
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": True,
        "openai": {
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "organization": "",
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama3",
        },
        "glm": {
            "api_key": "",
            "model": "glm-4",
        },
    },
    "voice": {
        "stt_backend": "system",
        "tts_backend": "system",
        "language": "zh-CN",
        "sample_rate": 16000,
        "channels": 1,
        "vad_enabled": True,
        "vad_threshold": 500,
        "vad_silence_duration": 1.0,
        "recording_timeout": 30,
    },
    "agent": {
        "system_prompt": (
            "You are VoicePilot, a helpful AI assistant. "
            "You can help users with various tasks including answering questions, "
            "performing calculations, checking weather, managing files, and setting timers. "
            "Respond concisely and clearly. If you don't know something, say so honestly."
        ),
        "max_history": 50,
        "max_context_tokens": 4096,
        "auto_save_history": True,
        "history_file": "~/.voicepilot/history.json",
    },
    "plugins": {
        "enabled": ["calculator", "weather", "file_ops", "timer"],
        "directory": "~/.voicepilot/plugins",
        "auto_load": True,
    },
    "tui": {
        "enabled": True,
        "theme": "dark",
        "show_timestamp": True,
        "show_tokens": False,
    },
    "logging": {
        "level": "INFO",
        "file": "~/.voicepilot/voicepilot.log",
        "max_size_mb": 10,
        "backup_count": 3,
    },
}


class VoicePilotConfig:
    """Configuration manager for VoicePilot-CLI.

    Loads configuration from ~/.voicepilot/config.yaml (or JSON fallback),
    merges with defaults, and provides access to individual settings.

    Attributes:
        config_path: Path to the configuration file.
        config_dir: Path to the configuration directory.
        _data: The merged configuration data.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize configuration manager.

        Args:
            config_path: Optional custom path to config file.
                        Defaults to ~/.voicepilot/config.json.
        """
        if config_path:
            self.config_path = Path(config_path)
            self.config_dir = self.config_path.parent
        else:
            self.config_dir = Path.home() / ".voicepilot"
            self.config_path = self.config_dir / "config.json"

        self._data: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        """Load configuration from file, merging with defaults.

        If the config file doesn't exist, creates it with defaults.
        Supports both JSON format.
        """
        if not self.config_path.exists():
            self._ensure_dir()
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._data = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), loaded)
        except (json.JSONDecodeError, IOError) as e:
            # If config is corrupted, use defaults and save
            import sys
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            print("Using default configuration.")
            self._data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries. Override values take precedence.

        Args:
            base: Base dictionary (defaults).
            override: Override dictionary (loaded config).

        Returns:
            Merged dictionary.
        """
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _ensure_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        """Save current configuration to file."""
        self._ensure_dir()
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save config to {self.config_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key path.

        Args:
            key: Dot-separated key path (e.g., 'llm.backend').
            default: Default value if key not found.

        Returns:
            Configuration value or default.

        Examples:
            >>> config = VoicePilotConfig()
            >>> config.get('llm.backend')
            'ollama'
            >>> config.get('llm.temperature')
            0.7
        """
        keys = key.split(".")
        value: Any = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-separated key path.

        Creates intermediate dictionaries as needed.

        Args:
            key: Dot-separated key path (e.g., 'llm.backend').
            value: Value to set.

        Examples:
            >>> config = VoicePilotConfig()
            >>> config.set('llm.backend', 'openai')
        """
        keys = key.split(".")
        data = self._data
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the full configuration as a dictionary.

        Returns:
            Complete configuration dictionary.
        """
        return copy.deepcopy(self._data)

    def reset_to_defaults(self) -> None:
        """Reset all configuration values to their defaults."""
        self._data = copy.deepcopy(DEFAULT_CONFIG)

    @property
    def llm_backend(self) -> str:
        """Get the configured LLM backend name.

        Returns:
            Backend name string (e.g., 'openai', 'ollama', 'glm').
        """
        return self.get("llm.backend", "ollama")

    @property
    def llm_model(self) -> str:
        """Get the configured LLM model name.

        Returns:
            Model name string.
        """
        return self.get("llm.model", "llama3")

    @property
    def stt_backend(self) -> str:
        """Get the configured STT backend name.

        Returns:
            STT backend name string.
        """
        return self.get("voice.stt_backend", "system")

    @property
    def tts_backend(self) -> str:
        """Get the configured TTS backend name.

        Returns:
            TTS backend name string.
        """
        return self.get("voice.tts_backend", "system")

    @property
    def system_prompt(self) -> str:
        """Get the configured system prompt.

        Returns:
            System prompt string.
        """
        return self.get("agent.system_prompt", "")

    @property
    def max_history(self) -> int:
        """Get the maximum conversation history length.

        Returns:
            Maximum history length as integer.
        """
        return int(self.get("agent.max_history", 50))

    @property
    def stream_enabled(self) -> bool:
        """Check if streaming LLM responses are enabled.

        Returns:
            True if streaming is enabled.
        """
        return bool(self.get("llm.stream", True))

    @property
    def temperature(self) -> float:
        """Get the LLM temperature setting.

        Returns:
            Temperature value as float.
        """
        return float(self.get("llm.temperature", 0.7))

    @property
    def max_tokens(self) -> int:
        """Get the maximum tokens for LLM responses.

        Returns:
            Maximum tokens as integer.
        """
        return int(self.get("llm.max_tokens", 2048))

    def get_backend_config(self, backend_name: str) -> Dict[str, Any]:
        """Get configuration specific to an LLM backend.

        Args:
            backend_name: Name of the backend (e.g., 'openai', 'ollama', 'glm').

        Returns:
            Backend-specific configuration dictionary.
        """
        return self.get(f"llm.{backend_name}", {})
