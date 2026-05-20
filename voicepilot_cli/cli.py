"""
CLI argument parser for VoicePilot-CLI.

Provides the main command-line interface with subcommands:
- chat: Start an interactive conversation session
- config: Manage configuration
- plugin: Manage plugins (list, install)
"""

import argparse
import sys
from typing import List, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for VoicePilot-CLI.

    Returns:
        Configured ArgumentParser instance with all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="voicepilot",
        description="VoicePilot-CLI: A lightweight local voice AI agent CLI engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  voicepilot chat                    Start text-mode chat
  voicepilot chat --mode voice       Start voice-mode chat
  voicepilot chat --model gpt-4      Use specific LLM model
  voicepilot config                  Show current configuration
  voicepilot config --set llm.backend openai
  voicepilot plugin list             List available plugins
  voicepilot plugin install weather  Install a plugin
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"VoicePilot-CLI {__import__('voicepilot_cli').__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── chat subcommand ──
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start an interactive conversation session",
        description="Start an interactive conversation with the AI agent. "
                    "Supports both text and voice modes.",
    )
    chat_parser.add_argument(
        "--mode", "-m",
        choices=["text", "voice"],
        default="text",
        help="Interaction mode: 'text' or 'voice' (default: text)",
    )
    chat_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name to use (overrides config)",
    )
    chat_parser.add_argument(
        "--backend",
        type=str,
        default=None,
        choices=["openai", "ollama", "glm"],
        help="LLM backend to use (overrides config)",
    )
    chat_parser.add_argument(
        "--system-prompt", "-s",
        type=str,
        default=None,
        help="Custom system prompt for the agent",
    )
    chat_parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable TUI dashboard, use plain text output",
    )
    chat_parser.add_argument(
        "--max-history",
        type=int,
        default=None,
        help="Maximum conversation history length (overrides config)",
    )
    chat_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # ── config subcommand ──
    config_parser = subparsers.add_parser(
        "config",
        help="Manage VoicePilot configuration",
        description="View and modify VoicePilot configuration settings.",
    )
    config_parser.add_argument(
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set a configuration value (e.g., --set llm.backend openai)",
    )
    config_parser.add_argument(
        "--get",
        type=str,
        metavar="KEY",
        help="Get a specific configuration value",
    )
    config_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset configuration to defaults",
    )
    config_parser.add_argument(
        "--path",
        action="store_true",
        help="Show configuration file path",
    )
    config_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open configuration file in default editor",
    )

    # ── plugin subcommand ──
    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Manage VoicePilot plugins",
        description="List, install, and manage VoicePilot plugins.",
    )
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command")

    # plugin list
    plugin_subparsers.add_parser(
        "list",
        help="List all available and installed plugins",
    )

    # plugin install
    install_parser = plugin_subparsers.add_parser(
        "install",
        help="Install a plugin",
    )
    install_parser.add_argument(
        "name",
        type=str,
        help="Name of the plugin to install",
    )
    install_parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to plugin file or directory",
    )

    # plugin uninstall
    uninstall_parser = plugin_subparsers.add_parser(
        "uninstall",
        help="Uninstall a plugin",
    )
    uninstall_parser.add_argument(
        "name",
        type=str,
        help="Name of the plugin to uninstall",
    )

    # plugin enable
    enable_parser = plugin_subparsers.add_parser(
        "enable",
        help="Enable a plugin",
    )
    enable_parser.add_argument(
        "name",
        type=str,
        help="Name of the plugin to enable",
    )

    # plugin disable
    disable_parser = plugin_subparsers.add_parser(
        "disable",
        help="Disable a plugin",
    )
    disable_parser.add_argument(
        "name",
        type=str,
        help="Name of the plugin to disable",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the VoicePilot CLI.

    Parses command-line arguments and dispatches to the appropriate handler.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # No command specified - show help
    if args.command is None:
        parser.print_help()
        return 0

    # Import here to avoid loading heavy modules for simple commands
    from voicepilot_cli.config import VoicePilotConfig
    from voicepilot_cli.utils.logger import get_logger

    logger = get_logger("cli")

    try:
        if args.command == "chat":
            return _handle_chat(args, logger)
        elif args.command == "config":
            return _handle_config(args, VoicePilotConfig(), logger)
        elif args.command == "plugin":
            return _handle_plugin(args, VoicePilotConfig(), logger)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nGoodbye!")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if getattr(args, "debug", False):
            import traceback
            traceback.print_exc()
        return 1


def _handle_chat(args: argparse.Namespace, logger) -> int:
    """Handle the 'chat' subcommand.

    Sets up and runs the interactive chat session.

    Args:
        args: Parsed command-line arguments.
        logger: Logger instance.

    Returns:
        Exit code.
    """
    from voicepilot_cli.config import VoicePilotConfig
    from voicepilot_cli.agent.core import AgentCore

    if args.debug:
        import logging
        logging.getLogger("voicepilot_cli").setLevel(logging.DEBUG)

    config = VoicePilotConfig()

    # Apply CLI overrides to config
    if args.backend:
        config.set("llm.backend", args.backend)
    if args.model:
        config.set("llm.model", args.model)
    if args.system_prompt:
        config.set("agent.system_prompt", args.system_prompt)
    if args.max_history is not None:
        config.set("agent.max_history", args.max_history)

    logger.info(f"Starting VoicePilot in {args.mode} mode")

    # Create and run the agent
    agent = AgentCore(config=config)

    if args.mode == "voice":
        return agent.run_voice_mode()
    else:
        return agent.run_text_mode(use_tui=not args.no_tui)


def _handle_config(args: argparse.Namespace, config, logger) -> int:
    """Handle the 'config' subcommand.

    Args:
        args: Parsed command-line arguments.
        config: VoicePilotConfig instance.
        logger: Logger instance.

    Returns:
        Exit code.
    """
    if args.path:
        print(config.config_path)
        return 0

    if args.reset:
        config.reset_to_defaults()
        config.save()
        print("Configuration reset to defaults.")
        return 0

    if args.edit:
        import os
        import subprocess
        editor = os.environ.get("EDITOR", "vi")
        subprocess.call([editor, config.config_path])
        return 0

    if args.set:
        key, value = args.set
        config.set(key, value)
        config.save()
        print(f"Set {key} = {value}")
        return 0

    if args.get:
        value = config.get(args.get)
        if value is None:
            print(f"Key '{args.get}' not found in configuration.")
            return 1
        print(f"{args.get} = {value}")
        return 0

    # No specific action - show full config
    config_data = config.to_dict()
    print("VoicePilot Configuration:")
    print("=" * 40)
    _print_dict(config_data, indent=0)
    return 0


def _handle_plugin(args: argparse.Namespace, config, logger) -> int:
    """Handle the 'plugin' subcommand.

    Args:
        args: Parsed command-line arguments.
        config: VoicePilotConfig instance.
        logger: Logger instance.

    Returns:
        Exit code.
    """
    from voicepilot_cli.plugins.registry import PluginRegistry

    registry = PluginRegistry(config=config)

    if args.plugin_command == "list":
        return _plugin_list(registry)
    elif args.plugin_command == "install":
        return _plugin_install(registry, args.name, args.path)
    elif args.plugin_command == "uninstall":
        return _plugin_uninstall(registry, args.name)
    elif args.plugin_command == "enable":
        return _plugin_enable(registry, args.name)
    elif args.plugin_command == "disable":
        return _plugin_disable(registry, args.name)
    else:
        print("Please specify a plugin action: list, install, uninstall, enable, disable")
        return 1


def _plugin_list(registry) -> int:
    """List all available plugins.

    Args:
        registry: PluginRegistry instance.

    Returns:
        Exit code.
    """
    plugins = registry.list_plugins()

    if not plugins:
        print("No plugins found.")
        return 0

    print("Available Plugins:")
    print("=" * 60)
    print(f"{'Name':<20} {'Status':<12} {'Description'}")
    print("-" * 60)

    for plugin_info in plugins:
        status = "enabled" if plugin_info.get("enabled", False) else "disabled"
        name = plugin_info.get("name", "unknown")
        desc = plugin_info.get("description", "No description")
        print(f"{name:<20} {status:<12} {desc}")

    return 0


def _plugin_install(registry, name: str, path: Optional[str]) -> int:
    """Install a plugin.

    Args:
        registry: PluginRegistry instance.
        name: Plugin name.
        path: Optional path to plugin file.

    Returns:
        Exit code.
    """
    try:
        registry.install_plugin(name, path=path)
        print(f"Plugin '{name}' installed successfully.")
        return 0
    except Exception as e:
        print(f"Failed to install plugin '{name}': {e}")
        return 1


def _plugin_uninstall(registry, name: str) -> int:
    """Uninstall a plugin.

    Args:
        registry: PluginRegistry instance.
        name: Plugin name.

    Returns:
        Exit code.
    """
    try:
        registry.uninstall_plugin(name)
        print(f"Plugin '{name}' uninstalled successfully.")
        return 0
    except Exception as e:
        print(f"Failed to uninstall plugin '{name}': {e}")
        return 1


def _plugin_enable(registry, name: str) -> int:
    """Enable a plugin.

    Args:
        registry: PluginRegistry instance.
        name: Plugin name.

    Returns:
        Exit code.
    """
    try:
        registry.enable_plugin(name)
        print(f"Plugin '{name}' enabled.")
        return 0
    except Exception as e:
        print(f"Failed to enable plugin '{name}': {e}")
        return 1


def _plugin_disable(registry, name: str) -> int:
    """Disable a plugin.

    Args:
        registry: PluginRegistry instance.
        name: Plugin name.

    Returns:
        Exit code.
    """
    try:
        registry.disable_plugin(name)
        print(f"Plugin '{name}' disabled.")
        return 0
    except Exception as e:
        print(f"Failed to disable plugin '{name}': {e}")
        return 1


def _print_dict(data: dict, indent: int) -> None:
    """Recursively print a dictionary with indentation.

    Args:
        data: Dictionary to print.
        indent: Current indentation level.
    """
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            _print_dict(value, indent + 1)
        else:
            print(f"{prefix}{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
