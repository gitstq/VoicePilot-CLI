"""
Logging utility for VoicePilot-CLI.

Provides a configured logger with console and optional file output.
Uses only Python stdlib logging module.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Logger name prefix for all VoicePilot loggers
LOGGER_PREFIX = "voicepilot_cli"

# Default log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level flag to prevent duplicate handler setup
_loggers_configured: set = set()


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a named logger instance.

    Creates or retrieves a logger with the given name, automatically
    prefixed with 'voicepilot_cli.'. The logger is configured with
    both console and optional file handlers.

    Args:
        name: Logger name (will be prefixed). Use short names like
              'agent', 'llm', 'tui', etc.
        level: Optional log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').
              If None, uses the default level.

    Returns:
        Configured logging.Logger instance.

    Examples:
        >>> logger = get_logger("agent")
        >>> logger.info("Agent started")
        >>> logger = get_logger("llm.openai", level="DEBUG")
    """
    full_name = f"{LOGGER_PREFIX}.{name}" if not name.startswith(LOGGER_PREFIX) else name
    logger = logging.getLogger(full_name)

    # Set level if specified
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Ensure handlers are configured (only once per logger)
    if full_name not in _loggers_configured:
        _setup_logger_handlers(logger)
        _loggers_configured.add(full_name)

    return logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 10,
    backup_count: int = 3,
    console_output: bool = True,
) -> logging.Logger:
    """Set up the root VoicePilot logger.

    Configures the root logger for all VoicePilot modules with
    console and optional file handlers.

    Args:
        level: Log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file: Optional path to log file. If None, no file logging.
        max_size_mb: Maximum log file size in MB before rotation.
        backup_count: Number of backup log files to keep.
        console_output: Whether to output to console.

    Returns:
        Root VoicePilot logger instance.

    Examples:
        >>> logger = setup_logging(level="DEBUG", log_file="~/voicepilot.log")
    """
    root_logger = logging.getLogger(LOGGER_PREFIX)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (with rotation)
    if log_file:
        log_path = Path(os.path.expanduser(log_file))
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # File always gets DEBUG level
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Mark as configured
    _loggers_configured.add(LOGGER_PREFIX)

    return root_logger


def _setup_logger_handlers(logger: logging.Logger) -> None:
    """Set up default handlers for a logger.

    Adds a console handler if the logger doesn't have any handlers
    and its parent chain doesn't have handlers.

    Args:
        logger: Logger to configure.
    """
    # Don't add handlers if the logger already has some
    if logger.handlers:
        return

    # Don't add handlers if a parent logger has them
    if logging.getLogger(LOGGER_PREFIX).handlers:
        return

    # Add a simple console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
