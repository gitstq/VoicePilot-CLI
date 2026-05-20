"""
TUI Dashboard for VoicePilot-CLI.

Provides a rich terminal-based dashboard for the chat interface.
Uses the Rich library for formatting and layout.
Falls back to plain text if Rich is not available.
"""

import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from voicepilot_cli.utils.logger import get_logger


class TUIDashboard:
    """Terminal UI dashboard for VoicePilot-CLI.

    Provides a rich, interactive chat interface with:
    - Styled message display
    - Status bar with backend/model info
    - Input prompt with history
    - Command completion

    Falls back to plain text mode if Rich is not available.
    """

    def __init__(self, agent: Any, config: Any) -> None:
        """Initialize the TUI dashboard.

        Args:
            agent: AgentCore instance.
            config: VoicePilotConfig instance.
        """
        self.agent = agent
        self.config = config
        self.logger = get_logger("tui")

        # Check Rich availability
        self._rich_available = self._check_rich()

        # Initialize theme
        theme_name = config.get("tui.theme", "dark")
        self._theme_colors: Dict[str, str] = {}
        if self._rich_available:
            from voicepilot_cli.tui.theme import ThemeManager
            self._theme = ThemeManager(theme_name)
            self._theme_colors = self._theme.to_dict()

        # Settings
        self._show_timestamp = config.get("tui.show_timestamp", True)
        self._show_tokens = config.get("tui.show_tokens", False)

        # Command history
        self._history: List[str] = []
        self._history_index = -1

        # Widgets
        self._status_items: Dict[str, str] = {}

    def _check_rich(self) -> bool:
        """Check if Rich library is available.

        Returns:
            True if Rich is installed.
        """
        try:
            from rich.console import Console  # noqa: F401
            from rich.markdown import Markdown  # noqa: F401
            from rich.panel import Panel  # noqa: F401
            return True
        except ImportError:
            return False

    def run(self) -> int:
        """Run the TUI dashboard.

        Starts the interactive chat loop with the TUI.

        Returns:
            Exit code.
        """
        if not self._rich_available:
            self.logger.warning("Rich not available, using plain text mode")
            return self.agent.run_text_mode(use_tui=False)

        return self._run_rich_dashboard()

    def _run_rich_dashboard(self) -> int:
        """Run the dashboard with Rich formatting.

        Returns:
            Exit code.
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.text import Text

        console = Console()

        # Display welcome banner
        self._print_welcome(console)

        # Update status bar
        self._update_status()

        try:
            while True:
                # Display input prompt
                prompt_text = self._format_input_prompt()
                console.print(prompt_text, end="")

                try:
                    user_input = input().strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input:
                    continue

                # Add to history
                self._history.append(user_input)
                self._history_index = len(self._history)

                # Handle commands
                if user_input.startswith("/"):
                    if self.agent._handle_command(user_input):
                        break
                    self._update_status()
                    continue

                # Display user message
                self._display_user_message(console, user_input)

                # Process and display response
                if self.config.stream_enabled:
                    self._display_streaming_response(console, user_input)
                else:
                    self._display_response(console, user_input)

                # Update status
                self._update_status()

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            self.logger.error(f"TUI error: {e}")
            return 1

        return 0

    def _print_welcome(self, console: Any) -> None:
        """Print the welcome banner.

        Args:
            console: Rich Console instance.
        """
        from rich.panel import Panel
        from rich.text import Text

        welcome_text = Text()
        welcome_text.append("VoicePilot-CLI", style="bold cyan")
        welcome_text.append(f"\nv{self.agent.__class__.__module__.split('.')[0].__version__ if hasattr(__import__('voicepilot_cli'), '__version__') else '0.1.0'}", style="dim")
        welcome_text.append("\n\nCommands: /help, /quit, /clear, /history", style="dim")
        welcome_text.append("\nType your message and press Enter", style="dim")

        panel = Panel(
            welcome_text,
            title="[bold]Welcome[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()

    def _format_input_prompt(self) -> str:
        """Format the input prompt.

        Returns:
            Rich-formatted prompt string.
        """
        color = self._theme_colors.get("input_prompt", "cyan")
        return f"[{color} bold]> You:[/{color} bold] "

    def _display_user_message(self, console: Any, message: str) -> None:
        """Display a user message.

        Args:
            console: Rich Console instance.
            message: User message text.
        """
        color = self._theme_colors.get("user_msg", "green")
        ts_color = self._theme_colors.get("timestamp", "dim")

        ts = ""
        if self._show_timestamp:
            ts = f"[{ts_color}]{datetime.now().strftime('%H:%M:%S')}[/{ts_color}] "

        console.print(f"{ts}[{color} bold]> You:[/{color} bold] {message}")

    def _display_response(self, console: Any, user_input: str) -> None:
        """Display a complete assistant response.

        Args:
            console: Rich Console instance.
            user_input: Original user input.
        """
        from rich.panel import Panel
        from rich.markdown import Markdown

        color = self._theme_colors.get("assistant_msg", "cyan")
        ts_color = self._theme_colors.get("timestamp", "dim")
        border_color = self._theme_colors.get("border", "dim")

        try:
            response = self.agent.process_input(user_input)
        except Exception as e:
            response = f"Error: {e}"

        ts = ""
        if self._show_timestamp:
            ts = f"[{ts_color}]{datetime.now().strftime('%H:%M:%S')}[/{ts_color}] "

        # Render markdown
        try:
            md = Markdown(response)
            panel = Panel(
                md,
                title=f"{ts}[{color} bold]Assistant[/{color} bold]",
                border_style=border_color,
                padding=(0, 1),
            )
            console.print(panel)
        except Exception:
            # Fallback to plain text if markdown rendering fails
            console.print(f"{ts}[{color} bold]Assistant:[/{color} bold] {response}")

    def _display_streaming_response(self, console: Any, user_input: str) -> None:
        """Display a streaming assistant response.

        Args:
            console: Rich Console instance.
            user_input: Original user input.
        """
        from rich.live import Live
        from rich.text import Text
        from rich.panel import Panel

        color = self._theme_colors.get("assistant_msg", "cyan")
        border_color = self._theme_colors.get("border", "dim")

        full_response = ""

        try:
            with Live(console=console, refresh_per_second=15) as live:
                response_text = Text()
                for chunk in self.agent.process_input_stream(user_input):
                    full_response += chunk
                    response_text.append(chunk)
                    panel = Panel(
                        response_text,
                        title=f"[{color} bold]Assistant (streaming)...[/{color} bold]",
                        border_style=border_color,
                        padding=(0, 1),
                    )
                    live.update(panel)

                # Final update with complete response
                from rich.markdown import Markdown
                try:
                    md = Markdown(full_response)
                    panel = Panel(
                        md,
                        title=f"[{color} bold]Assistant[/{color} bold]",
                        border_style=border_color,
                        padding=(0, 1),
                    )
                    live.update(panel)
                except Exception:
                    panel = Panel(
                        response_text,
                        title=f"[{color} bold]Assistant[/{color} bold]",
                        border_style=border_color,
                        padding=(0, 1),
                    )
                    live.update(panel)

        except Exception as e:
            console.print(f"[red]Streaming error: {e}[/red]")

    def _update_status(self) -> None:
        """Update the status bar information."""
        backend_name = self.config.llm_backend
        model_name = self.config.llm_model
        history_count = self.agent.memory.message_count

        self._status_items = {
            "Backend": backend_name,
            "Model": model_name,
            "History": str(history_count),
            "Theme": self.config.get("tui.theme", "dark"),
        }

    def _print_status_bar(self, console: Any) -> None:
        """Print the status bar.

        Args:
            console: Rich Console instance.
        """
        from rich.text import Text

        border_color = self._theme_colors.get("border", "dim")
        text_color = self._theme_colors.get("text_dim", "dim")

        parts = [f"[{text_color}]{k}: {v}[/{text_color}]" for k, v in self._status_items.items()]
        content = f" [{border_color}]|[/] ".join(parts)

        status_text = Text.from_markup(f"[{border_color}]─[/] {content} [{border_color}]─[/]")
        console.print(status_text)

    def _handle_history_navigation(self, direction: str) -> Optional[str]:
        """Navigate command history.

        Args:
            direction: 'up' or 'down'.

        Returns:
            History entry or None.
        """
        if not self._history:
            return None

        if direction == "up" and self._history_index > 0:
            self._history_index -= 1
            return self._history[self._history_index]
        elif direction == "down" and self._history_index < len(self._history) - 1:
            self._history_index += 1
            return self._history[self._history_index]

        return None
