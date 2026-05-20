"""
Plugin base class for VoicePilot-CLI.

All plugins must inherit from PluginBase and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PluginBase(ABC):
    """Abstract base class for VoicePilot plugins.

    Provides the interface that all plugins must implement.
    Plugins can handle specific types of user requests and
    extend the agent's capabilities.

    Attributes:
        _config: Optional plugin configuration dictionary.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin.

        Args:
            config: Optional configuration dictionary for the plugin.
        """
        self._config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the unique name of the plugin.

        Returns:
            Plugin name string (used as identifier).
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Get a description of what the plugin does.

        Returns:
            Description string.
        """
        ...

    @property
    def version(self) -> str:
        """Get the plugin version.

        Returns:
            Version string (default: '1.0.0').
        """
        return "1.0.0"

    @property
    def author(self) -> str:
        """Get the plugin author.

        Returns:
            Author string (default: 'unknown').
        """
        return "unknown"

    @abstractmethod
    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute the plugin with the given command.

        This is the main entry point for plugin execution.
        The command string is parsed by the plugin to determine
        the specific action to perform.

        Args:
            command: Command string from the user or task planner.
            **kwargs: Additional parameters.

        Returns:
            Result string to be displayed to the user.
        """
        ...

    def can_handle(self, input_text: str) -> bool:
        """Check if this plugin can handle the given input.

        Override this method to provide custom input matching logic.
        The default implementation checks if any trigger keywords
        are present in the input.

        Args:
            input_text: User input text to check.

        Returns:
            True if this plugin can handle the input.
        """
        triggers = self.get_trigger_keywords()
        if not triggers:
            return False
        input_lower = input_text.lower()
        return any(trigger.lower() in input_lower for trigger in triggers)

    @property
    def trigger_keywords(self) -> List[str]:
        """Get keywords that trigger this plugin.

        Override this property to define when the plugin should
        be automatically activated.

        Returns:
            List of trigger keyword strings.
        """
        return []

    def get_trigger_keywords(self) -> List[str]:
        """Get trigger keywords (alias for trigger_keywords property).

        Returns:
            List of trigger keyword strings.
        """
        return self.trigger_keywords

    @property
    def commands(self) -> List[str]:
        """Get list of supported commands.

        Returns:
            List of command strings this plugin supports.
        """
        return []

    def on_load(self) -> None:
        """Called when the plugin is loaded.

        Override to perform initialization tasks when the plugin
        is first loaded by the registry.
        """
        pass

    def on_unload(self) -> None:
        """Called when the plugin is unloaded.

        Override to perform cleanup tasks.
        """
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a plugin configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value.
        """
        return self._config.get(key, default)

    def get_info(self) -> Dict[str, Any]:
        """Get plugin metadata.

        Returns:
            Dictionary with plugin information.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "commands": self.commands,
            "triggers": self.trigger_keywords,
        }

    def __repr__(self) -> str:
        return f"Plugin(name={self.name!r}, version={self.version!r})"
