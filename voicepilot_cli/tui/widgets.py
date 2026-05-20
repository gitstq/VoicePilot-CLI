"""
Custom TUI widgets for VoicePilot-CLI.

Provides reusable Rich-based widgets for the terminal dashboard.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from voicepilot_cli.utils.logger import get_logger


class MarkdownRenderer:
    """Simple markdown-to-rich-text renderer.

    Converts basic markdown syntax to Rich-compatible markup
    for display in the TUI.
    """

    @staticmethod
    def render(text: str) -> str:
        """Convert markdown text to Rich markup.

        Supports:
        - **bold** -> [bold]text[/bold]
        - *italic* -> [italic]text[/italic]
        - `code` -> [cyan]text[/cyan]
        - ```code blocks``` -> [dim]text[/dim]
        - # headings -> [bold]text[/bold]

        Args:
            text: Markdown text.

        Returns:
            Rich markup string.
        """
        import re

        # Code blocks (```...```)
        text = re.sub(
            r"```(\w*)\n(.*?)```",
            lambda m: f"[dim cyan]{m.group(2).strip()}[/dim cyan]",
            text,
            flags=re.DOTALL,
        )

        # Inline code
        text = re.sub(r"`([^`]+)`", r"[cyan]\1[/cyan]", text)

        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"[bold]\1[/bold]", text)

        # Italic
        text = re.sub(r"\*(.+?)\*", r"[italic]\1[/italic]", text)

        # Headers
        text = re.sub(r"^### (.+)$", r"[bold dim]\1[/bold dim]", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"[bold]\1[/bold]", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.+)$", r"[bold underline]\1[/bold underline]", text, flags=re.MULTILINE)

        # Lists
        text = re.sub(r"^- (.+)$", r"  [dim]-[/dim] \1", text, flags=re.MULTILINE)
        text = re.sub(r"^\* (.+)$", r"  [dim]*[/dim] \1", text, flags=re.MULTILINE)

        return text


class MessageBubble:
    """Represents a chat message bubble for display.

    Formats messages with role indicators, timestamps,
    and appropriate styling.
    """

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        show_timestamp: bool = True,
    ) -> None:
        """Initialize a message bubble.

        Args:
            role: Message role ('user', 'assistant', 'system', 'tool').
            content: Message content.
            timestamp: ISO timestamp string.
            show_timestamp: Whether to display timestamp.
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.show_timestamp = show_timestamp

    def format_plain(self) -> str:
        """Format message as plain text.

        Returns:
            Plain text formatted message.
        """
        ts = ""
        if self.show_timestamp:
            ts = f"[{self.timestamp[:19]}] "

        role_labels = {
            "user": "You",
            "assistant": "Assistant",
            "system": "System",
            "tool": "Tool",
        }
        label = role_labels.get(self.role, self.role)

        return f"{ts}{label}: {self.content}"

    def format_rich(self, theme_colors: Optional[Dict[str, str]] = None) -> str:
        """Format message with Rich markup.

        Args:
            theme_colors: Optional theme color dictionary.

        Returns:
            Rich markup formatted message.
        """
        if not theme_colors:
            theme_colors = {}

        ts = ""
        if self.show_timestamp:
            ts_color = theme_colors.get("timestamp", "dim")
            ts = f"[{ts_color}]{self.timestamp[:19]}[/{ts_color}] "

        role_config = {
            "user": {
                "label": "You",
                "color": theme_colors.get("user_msg", "green"),
                "prefix": ">",
            },
            "assistant": {
                "label": "Assistant",
                "color": theme_colors.get("assistant_msg", "cyan"),
                "prefix": "",
            },
            "system": {
                "label": "System",
                "color": theme_colors.get("system_msg", "yellow"),
                "prefix": "!",
            },
            "tool": {
                "label": "Tool",
                "color": theme_colors.get("text_dim", "dim"),
                "prefix": "#",
            },
        }

        config = role_config.get(self.role, role_config["system"])
        color = config["color"]
        label = config["label"]
        prefix = config["prefix"]

        # Render markdown in content
        rendered_content = MarkdownRenderer.render(self.content)

        return (
            f"{ts}[{color} bold]{prefix} {label}:[/{color} bold]\n"
            f"  {rendered_content}"
        )


class StatusBar:
    """Status bar widget showing system information.

    Displays backend status, model info, and other metadata.
    """

    def __init__(self) -> None:
        """Initialize the status bar."""
        self._items: List[Dict[str, str]] = []

    def set_item(self, key: str, value: str, color: str = "") -> None:
        """Set a status bar item.

        Args:
            key: Item identifier.
            value: Display value.
            color: Optional Rich color for the value.
        """
        # Update existing or add new
        for item in self._items:
            if item["key"] == key:
                item["value"] = value
                item["color"] = color
                return
        self._items.append({"key": key, "value": value, "color": color})

    def remove_item(self, key: str) -> None:
        """Remove a status bar item.

        Args:
            key: Item identifier to remove.
        """
        self._items = [item for item in self._items if item["key"] != key]

    def format_plain(self) -> str:
        """Format status bar as plain text.

        Returns:
            Plain text status bar.
        """
        parts = [f"{item['key']}: {item['value']}" for item in self._items]
        return " | ".join(parts)

    def format_rich(self, theme_colors: Optional[Dict[str, str]] = None) -> str:
        """Format status bar with Rich markup.

        Args:
            theme_colors: Optional theme color dictionary.

        Returns:
            Rich markup formatted status bar.
        """
        if not theme_colors:
            theme_colors = {}

        border_color = theme_colors.get("border", "dim")
        text_color = theme_colors.get("text_dim", "dim")

        parts = []
        for item in self._items:
            value_color = item.get("color", text_color)
            parts.append(
                f"[{text_color}]{item['key']}:[/{text_color}] "
                f"[{value_color}]{item['value']}[/{value_color}]"
            )

        content = f" [{border_color}]|[/] ".join(parts)
        return f"[{border_color}]─[/] {content} [{border_color}]─[/]"


class InputPrompt:
    """Custom input prompt widget.

    Provides a styled input prompt with optional prefix
    and character counter.
    """

    def __init__(
        self,
        prefix: str = ">",
        prompt_text: str = "You",
        color: str = "cyan",
    ) -> None:
        """Initialize the input prompt.

        Args:
            prefix: Prompt prefix character.
            prompt_text: Prompt label text.
            color: Rich color for the prompt.
        """
        self.prefix = prefix
        self.prompt_text = prompt_text
        self.color = color

    def format_plain(self) -> str:
        """Format prompt as plain text.

        Returns:
            Plain text prompt string.
        """
        return f"{self.prefix} {self.prompt_text}: "

    def format_rich(self) -> str:
        """Format prompt with Rich markup.

        Returns:
            Rich markup prompt string.
        """
        return f"[{self.color} bold]{self.prefix} {self.prompt_text}:[/{self.color} bold] "

    def get_input(self, plain_mode: bool = False) -> str:
        """Display prompt and get user input.

        Args:
            plain_mode: Whether to use plain text mode.

        Returns:
            User input string.
        """
        if plain_mode:
            prompt = self.format_plain()
        else:
            prompt = self.format_rich()

        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return ""


class ProgressBar:
    """Simple progress bar widget.

    Displays a text-based progress indicator.
    """

    def __init__(
        self,
        total: int = 100,
        width: int = 40,
        fill_char: str = "=",
        empty_char: str = "-",
    ) -> None:
        """Initialize the progress bar.

        Args:
            total: Total value representing 100%.
            width: Character width of the bar.
            fill_char: Character for filled portion.
            empty_char: Character for empty portion.
        """
        self.total = total
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
        self._current = 0

    def update(self, current: int) -> str:
        """Update progress and return formatted bar.

        Args:
            current: Current progress value.

        Returns:
            Formatted progress bar string.
        """
        self._current = min(current, self.total)
        ratio = self._current / self.total if self.total > 0 else 0
        filled = int(self.width * ratio)
        empty = self.width - filled
        percent = ratio * 100

        bar = self.fill_char * filled + self.empty_char * empty
        return f"[{bar}] {percent:.0f}% ({self._current}/{self.total})"

    def format_plain(self, current: int) -> str:
        """Format progress bar as plain text.

        Args:
            current: Current progress value.

        Returns:
            Plain text progress bar.
        """
        return self.update(current)

    def reset(self) -> None:
        """Reset progress to zero."""
        self._current = 0
