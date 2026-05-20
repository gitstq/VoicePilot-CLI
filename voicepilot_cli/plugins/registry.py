"""
Plugin registry and loader for VoicePilot-CLI.

Manages plugin discovery, loading, enabling/disabling,
and execution routing.
"""

import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from voicepilot_cli.plugins.base import PluginBase
from voicepilot_cli.utils.logger import get_logger


class PluginRegistry:
    """Plugin registry that manages all plugins.

    Handles plugin discovery, loading, lifecycle management,
    and routing user requests to appropriate plugins.

    Attributes:
        config: VoicePilotConfig instance.
        plugins_dir: Directory for external plugins.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        """Initialize the plugin registry.

        Args:
            config: Optional VoicePilotConfig instance.
        """
        self.logger = get_logger("plugins")
        self._config = config
        self._plugins: Dict[str, PluginBase] = {}
        self._enabled_plugins: set = set()
        self._disabled_plugins: set = set()

        # Determine plugin directory
        if config:
            plugins_dir = config.get("plugins.directory", "~/.voicepilot/plugins")
            auto_load = config.get("plugins.auto_load", True)
            enabled_names = config.get("plugins.enabled", [])
        else:
            plugins_dir = "~/.voicepilot/plugins"
            auto_load = True
            enabled_names = []

        self.plugins_dir = Path(os.path.expanduser(plugins_dir))

        # Load built-in plugins
        self._load_builtin_plugins()

        # Load enabled plugins from config
        for name in enabled_names:
            if name in self._plugins:
                self._enabled_plugins.add(name)

        # Load external plugins from directory
        if auto_load:
            self._load_external_plugins()

        self.logger.info(
            f"Plugin registry initialized: {len(self._plugins)} plugins, "
            f"{len(self._enabled_plugins)} enabled"
        )

    def _load_builtin_plugins(self) -> None:
        """Load all built-in plugins."""
        builtin_plugins = [
            ("voicepilot_cli.plugins.calculator", "CalculatorPlugin"),
            ("voicepilot_cli.plugins.weather", "WeatherPlugin"),
            ("voicepilot_cli.plugins.file_ops", "FileOpsPlugin"),
            ("voicepilot_cli.plugins.timer", "TimerPlugin"),
        ]

        for module_path, class_name in builtin_plugins:
            try:
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)
                plugin = plugin_class()
                self._plugins[plugin.name] = plugin
                self.logger.debug(f"Loaded built-in plugin: {plugin.name}")
            except Exception as e:
                self.logger.warning(f"Failed to load plugin {module_path}: {e}")

    def _load_external_plugins(self) -> None:
        """Load plugins from the external plugins directory.

        Scans the plugins directory for Python files and attempts
        to load them as plugins. Each file should contain a class
        that inherits from PluginBase.
        """
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        for py_file in self.plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                self._load_plugin_from_file(py_file)
            except Exception as e:
                self.logger.warning(f"Failed to load external plugin {py_file}: {e}")

    def _load_plugin_from_file(self, filepath: Path) -> None:
        """Load a plugin from a Python file.

        Args:
            filepath: Path to the plugin Python file.
        """
        module_name = f"voicepilot_external_plugin_{filepath.stem}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)

        if spec is None or spec.loader is None:
            self.logger.warning(f"Cannot create module spec for {filepath}")
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)

            # Find PluginBase subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin = attr()
                    self._plugins[plugin.name] = plugin
                    self._enabled_plugins.add(plugin.name)
                    self.logger.info(f"Loaded external plugin: {plugin.name} from {filepath}")
                    plugin.on_load()
                    break
        except Exception as e:
            self.logger.warning(f"Error loading plugin from {filepath}: {e}")

    def register(self, plugin: PluginBase, enabled: bool = True) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin instance to register.
            enabled: Whether to enable the plugin immediately.
        """
        self._plugins[plugin.name] = plugin
        if enabled:
            self._enabled_plugins.add(plugin.name)
            plugin.on_load()
        self.logger.info(f"Registered plugin: {plugin.name} (enabled={enabled})")

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name.

        Args:
            name: Plugin name to unregister.
        """
        if name in self._plugins:
            plugin = self._plugins[name]
            plugin.on_unload()
            del self._plugins[name]
            self._enabled_plugins.discard(name)
            self._disabled_plugins.discard(name)
            self.logger.info(f"Unregistered plugin: {name}")

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            Plugin instance or None if not found.
        """
        return self._plugins.get(name)

    def execute_matching(self, input_text: str) -> Optional[str]:
        """Find and execute a plugin that can handle the input.

        Iterates through enabled plugins and executes the first
        one that can handle the input.

        Args:
            input_text: User input text.

        Returns:
            Plugin result string or None if no plugin matched.
        """
        for name in self._enabled_plugins:
            plugin = self._plugins.get(name)
            if plugin and plugin.can_handle(input_text):
                try:
                    result = plugin.execute(input_text)
                    if result:
                        return result
                except Exception as e:
                    self.logger.error(f"Plugin {name} execution error: {e}")
        return None

    def execute_plugin(self, name: str, command: str, **kwargs: Any) -> Optional[str]:
        """Execute a specific plugin by name.

        Args:
            name: Plugin name.
            command: Command to execute.
            **kwargs: Additional parameters.

        Returns:
            Plugin result or None.
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            self.logger.warning(f"Plugin not found: {name}")
            return None

        if name not in self._enabled_plugins:
            self.logger.warning(f"Plugin {name} is disabled")
            return None

        try:
            return plugin.execute(command, **kwargs)
        except Exception as e:
            self.logger.error(f"Plugin {name} execution error: {e}")
            return None

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin.

        Args:
            name: Plugin name.

        Raises:
            KeyError: If plugin not found.
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin not found: {name}")
        self._enabled_plugins.add(name)
        self._disabled_plugins.discard(name)
        self._plugins[name].on_load()

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin.

        Args:
            name: Plugin name.

        Raises:
            KeyError: If plugin not found.
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin not found: {name}")
        self._enabled_plugins.discard(name)
        self._disabled_plugins.add(name)

    def install_plugin(self, name: str, path: Optional[str] = None) -> None:
        """Install a plugin from a file path or URL.

        If a path is provided, copies the plugin file to the plugins directory.
        If no path, creates a template plugin file.

        Args:
            name: Plugin name.
            path: Optional path to plugin file.

        Raises:
            FileNotFoundError: If path doesn't exist.
        """
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        if path:
            src = Path(path)
            if not src.exists():
                raise FileNotFoundError(f"Plugin file not found: {path}")
            import shutil
            dst = self.plugins_dir / src.name
            shutil.copy2(src, dst)
            self._load_plugin_from_file(dst)
        else:
            # Create a template plugin
            template = self._generate_plugin_template(name)
            dst = self.plugins_dir / f"{name}.py"
            with open(dst, "w", encoding="utf-8") as f:
                f.write(template)
            self._load_plugin_from_file(dst)

    def uninstall_plugin(self, name: str) -> None:
        """Uninstall and remove a plugin.

        Args:
            name: Plugin name.

        Raises:
            KeyError: If plugin not found.
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin not found: {name}")

        # Check if it's an external plugin
        plugin_file = self.plugins_dir / f"{name}.py"
        if plugin_file.exists():
            plugin_file.unlink()

        self.unregister(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins with their status.

        Returns:
            List of plugin info dictionaries.
        """
        result = []
        for name, plugin in self._plugins.items():
            info = plugin.get_info()
            info["enabled"] = name in self._enabled_plugins
            info["builtin"] = not (self.plugins_dir / f"{name}.py").exists()
            result.append(info)
        return result

    def reload_plugin(self, name: str) -> None:
        """Reload a plugin (hot-reload).

        Args:
            name: Plugin name.

        Raises:
            KeyError: If plugin not found.
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin not found: {name}")

        plugin = self._plugins[name]
        plugin.on_unload()

        plugin_file = self.plugins_dir / f"{name}.py"
        if plugin_file.exists():
            self._load_plugin_from_file(plugin_file)

    def _generate_plugin_template(self, name: str) -> str:
        """Generate a template plugin file.

        Args:
            name: Plugin name.

        Returns:
            Template Python code as string.
        """
        class_name = "".join(word.capitalize() for word in name.split("_"))
        return f'''"""
{name} plugin for VoicePilot-CLI.

Auto-generated plugin template.
"""

from typing import Any, Dict, List
from voicepilot_cli.plugins.base import PluginBase


class {class_name}Plugin(PluginBase):
    """Custom {name} plugin."""

    @property
    def name(self) -> str:
        return "{name}"

    @property
    def description(self) -> str:
        return "A custom plugin for {name}"

    @property
    def trigger_keywords(self) -> List[str]:
        return ["{name}"]

    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute the plugin.

        Args:
            command: Command string.
            **kwargs: Additional parameters.

        Returns:
            Result string.
        """
        # Implement your plugin logic here
        return f"[{self.name}] Received: {{command}}"
'''
