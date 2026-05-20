"""Plugins module for VoicePilot-CLI.

Provides a plugin system with base class, registry, and built-in plugins.
"""

from voicepilot_cli.plugins.base import PluginBase
from voicepilot_cli.plugins.registry import PluginRegistry

__all__ = ["PluginBase", "PluginRegistry"]
