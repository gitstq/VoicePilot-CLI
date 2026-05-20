"""
Color themes for VoicePilot TUI.

Provides predefined color themes for the terminal dashboard.
"""

from typing import Any, Dict, Tuple


class ThemeColors:
    """Color definitions for TUI themes.

    Each theme defines colors for different UI elements.
    Colors are specified as Rich-compatible color strings.
    """

    # Theme definitions: name -> color mapping
    THEMES: Dict[str, Dict[str, str]] = {
        "dark": {
            "primary": "cyan",
            "secondary": "blue",
            "accent": "magenta",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "info": "cyan",
            "text": "white",
            "text_dim": "bright_black",
            "border": "bright_black",
            "background": "black",
            "user_msg": "green",
            "assistant_msg": "cyan",
            "system_msg": "yellow",
            "timestamp": "bright_black",
            "input_prompt": "cyan",
            "input_border": "blue",
            "header": "bold cyan",
            "footer": "dim",
            "highlight": "bold white on blue",
            "code": "bright_yellow",
            "link": "underline blue",
        },
        "light": {
            "primary": "blue",
            "secondary": "deep_sky_blue4",
            "accent": "magenta",
            "success": "green",
            "warning": "dark_orange",
            "error": "red",
            "info": "dodger_blue",
            "text": "black",
            "text_dim": "grey50",
            "border": "grey70",
            "background": "white",
            "user_msg": "dark_green",
            "assistant_msg": "blue",
            "system_msg": "dark_orange",
            "timestamp": "grey50",
            "input_prompt": "blue",
            "input_border": "grey70",
            "header": "bold blue",
            "footer": "dim",
            "highlight": "bold black on grey85",
            "code": "dark_goldenrod",
            "link": "underline blue",
        },
        "monokai": {
            "primary": "#a6e22e",
            "secondary": "#66d9ef",
            "accent": "#ae81ff",
            "success": "#a6e22e",
            "warning": "#e6db74",
            "error": "#f92672",
            "info": "#66d9ef",
            "text": "#f8f8f2",
            "text_dim": "#75715e",
            "border": "#49483e",
            "background": "#272822",
            "user_msg": "#a6e22e",
            "assistant_msg": "#66d9ef",
            "system_msg": "#e6db74",
            "timestamp": "#75715e",
            "input_prompt": "#a6e22e",
            "input_border": "#49483e",
            "header": "bold #a6e22e",
            "footer": "dim #75715e",
            "highlight": "bold #f8f8f2 on #49483e",
            "code": "#e6db74",
            "link": "underline #66d9ef",
        },
        "dracula": {
            "primary": "#bd93f9",
            "secondary": "#8be9fd",
            "accent": "#ff79c6",
            "success": "#50fa7b",
            "warning": "#f1fa8c",
            "error": "#ff5555",
            "info": "#8be9fd",
            "text": "#f8f8f2",
            "text_dim": "#6272a4",
            "border": "#44475a",
            "background": "#282a36",
            "user_msg": "#50fa7b",
            "assistant_msg": "#bd93f9",
            "system_msg": "#f1fa8c",
            "timestamp": "#6272a4",
            "input_prompt": "#bd93f9",
            "input_border": "#44475a",
            "header": "bold #bd93f9",
            "footer": "dim #6272a4",
            "highlight": "bold #f8f8f2 on #44475a",
            "code": "#f1fa8c",
            "link": "underline #8be9fd",
        },
        "solarized_dark": {
            "primary": "#268bd2",
            "secondary": "#2aa198",
            "accent": "#d33682",
            "success": "#859900",
            "warning": "#b58900",
            "error": "#dc322f",
            "info": "#268bd2",
            "text": "#839496",
            "text_dim": "#586e75",
            "border": "#073642",
            "background": "#002b36",
            "user_msg": "#859900",
            "assistant_msg": "#268bd2",
            "system_msg": "#b58900",
            "timestamp": "#586e75",
            "input_prompt": "#268bd2",
            "input_border": "#073642",
            "header": "bold #268bd2",
            "footer": "dim #586e75",
            "highlight": "bold #93a1a1 on #073642",
            "code": "#b58900",
            "link": "underline #268bd2",
        },
    }

    @classmethod
    def get_theme(cls, name: str) -> Dict[str, str]:
        """Get a theme by name.

        Args:
            name: Theme name (e.g., 'dark', 'light', 'monokai', 'dracula').

        Returns:
            Theme color dictionary. Falls back to 'dark' if not found.
        """
        return cls.THEMES.get(name, cls.THEMES["dark"])

    @classmethod
    def list_themes(cls) -> list:
        """List all available theme names.

        Returns:
            List of theme name strings.
        """
        return list(cls.THEMES.keys())

    @classmethod
    def get_color(cls, theme_name: str, element: str) -> str:
        """Get a specific color from a theme.

        Args:
            theme_name: Theme name.
            element: UI element name (e.g., 'primary', 'text', 'border').

        Returns:
            Color string.
        """
        theme = cls.get_theme(theme_name)
        return theme.get(element, "white")


class ThemeManager:
    """Manages the active TUI theme.

    Allows runtime theme switching and provides
    easy access to theme colors.
    """

    def __init__(self, theme_name: str = "dark") -> None:
        """Initialize the theme manager.

        Args:
            theme_name: Initial theme name.
        """
        self._current_theme = theme_name
        self._colors = ThemeColors.get_theme(theme_name)

    @property
    def name(self) -> str:
        """Get the current theme name.

        Returns:
            Theme name string.
        """
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Switch to a different theme.

        Args:
            theme_name: Name of the theme to switch to.
        """
        self._current_theme = theme_name
        self._colors = ThemeColors.get_theme(theme_name)

    def get(self, element: str) -> str:
        """Get a color for a UI element.

        Args:
            element: UI element name.

        Returns:
            Color string.
        """
        return self._colors.get(element, "white")

    def to_dict(self) -> Dict[str, str]:
        """Get the full theme as a dictionary.

        Returns:
            Complete theme color dictionary.
        """
        return dict(self._colors)

    def __repr__(self) -> str:
        return f"ThemeManager(theme={self._current_theme!r})"
