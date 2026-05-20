"""
Helper functions for VoicePilot-CLI.

Provides common utility functions used across modules.
"""

import importlib
import os
import re
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length with suffix.

    Args:
        text: Input text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text string.

    Examples:
        >>> truncate_text("Hello World", 8)
        'Hello...'
        >>> truncate_text("Hi", 10)
        'Hi'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_bytes(size: int) -> str:
    """Format a byte count into a human-readable string.

    Args:
        size: Size in bytes.

    Returns:
        Formatted size string (e.g., '1.5 KB', '2.3 MB').

    Examples:
        >>> format_bytes(1024)
        '1.0 KB'
        >>> format_bytes(1536000)
        '1.5 MB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string.

    Uses a simple heuristic: approximately 4 characters per token
    for English text, and approximately 2 characters per token
    for Chinese text.

    Args:
        text: Input text.

    Returns:
        Estimated token count.

    Examples:
        >>> estimate_tokens("Hello world")
        3
    """
    if not text:
        return 0

    # Count Chinese characters
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other_chars = len(text) - chinese_chars

    # Chinese: ~1.5 chars per token, English: ~4 chars per token
    tokens = int(chinese_chars / 1.5 + other_chars / 4.0)
    return max(1, tokens)


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks.

    Removes or escapes potentially dangerous characters and patterns.

    Args:
        text: Raw user input.

    Returns:
        Sanitized text string.
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove ANSI escape sequences
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)

    # Remove control characters (except newline, tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Trim whitespace
    text = text.strip()

    return text


def check_dependency(package_name: str, import_name: Optional[str] = None) -> bool:
    """Check if a Python package is installed.

    Args:
        package_name: Package name as used in pip install.
        import_name: Module name to import (if different from package_name).

    Returns:
        True if the package is importable.

    Examples:
        >>> check_dependency("openai")
        True
        >>> check_dependency("pyttsx3")
        False
    """
    module_name = import_name or package_name
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def get_dependency_version(package_name: str) -> Optional[str]:
    """Get the version of an installed package.

    Args:
        package_name: Package name.

    Returns:
        Version string or None if not installed.
    """
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", None)
        if version is None:
            # Try pkg_resources
            try:
                import pkg_resources
                version = pkg_resources.get_distribution(package_name).version
            except Exception:
                pass
        return version
    except ImportError:
        return None


def ensure_directory(path: str) -> str:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path.

    Returns:
        Absolute path to the directory.
    """
    abs_path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def safe_filename(filename: str) -> str:
    """Convert a string to a safe filename.

    Removes or replaces characters that are not safe for filenames.

    Args:
        filename: Desired filename.

    Returns:
        Safe filename string.
    """
    # Remove/replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(" .")
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    # Ensure non-empty
    if not filename:
        filename = "unnamed"
    return filename


class Timer:
    """Context manager for timing code execution.

    Measures elapsed time for code blocks.

    Attributes:
        elapsed: Elapsed time in seconds.

    Examples:
        >>> with Timer() as t:
        ...     time.sleep(0.1)
        >>> print(f"Elapsed: {t.elapsed:.3f}s")
        Elapsed: 0.100s
    """

    def __init__(self) -> None:
        """Initialize the timer."""
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self._start_time = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._end_time = time.monotonic()
        self.elapsed = self._end_time - self._start_time

    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.monotonic()

    def stop(self) -> float:
        """Stop the timer and return elapsed time.

        Returns:
            Elapsed time in seconds.
        """
        self._end_time = time.monotonic()
        self.elapsed = self._end_time - self._start_time
        return self.elapsed

    def reset(self) -> None:
        """Reset the timer."""
        self._start_time = 0.0
        self._end_time = 0.0
        self.elapsed = 0.0


@contextmanager
def suppress_output() -> Generator[None, None, None]:
    """Context manager to suppress stdout and stderr.

    Useful for silencing noisy library output.

    Examples:
        >>> with suppress_output():
        ...     print("This won't be visible")
    """
    import sys

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = open(os.devnull, "w")  # noqa: SIM115
        sys.stderr = open(os.devnull, "w")  # noqa: SIM115
        yield
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def detect_language(text: str) -> str:
    """Detect the primary language of text.

    Uses a simple heuristic based on character analysis.

    Args:
        text: Input text.

    Returns:
        Language code ('zh', 'en', 'ja', 'ko', 'other').
    """
    if not text:
        return "other"

    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    japanese = sum(1 for c in text if "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff")
    korean = sum(1 for c in text if "\uac00" <= c <= "\ud7af" or "\u1100" <= c <= "\u11ff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())

    total = chinese + japanese + korean + latin
    if total == 0:
        return "other"

    scores = {
        "zh": chinese / total,
        "ja": japanese / total,
        "ko": korean / total,
        "en": latin / total,
    }

    return max(scores, key=scores.get)  # type: ignore
