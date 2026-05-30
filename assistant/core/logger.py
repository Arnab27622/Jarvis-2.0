"""
Structured Logging System for Jarvis 2.0

Replaces scattered print() calls with Python's logging module.
Provides per-module loggers with console (colorized) and rotating file output.

Usage:
    from assistant.core.logger import get_logger

    logger = get_logger("LLM")
    logger.info("Gemini response received")
    logger.error("API call failed: %s", error)
    logger.debug("Raw response: %s", data)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Color codes for terminal output
_COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET": "\033[0m",
    "TAG": "\033[34m",        # Blue (for module name)
}


class ColoredFormatter(logging.Formatter):
    """Colorized formatter for console output."""

    def format(self, record: logging.LogRecord) -> str:
        level_color = _COLORS.get(record.levelname, _COLORS["RESET"])
        tag_color = _COLORS["TAG"]
        reset = _COLORS["RESET"]

        # Save original attributes we are about to modify for format string evaluation
        original_levelname = record.levelname
        original_name = record.name

        # Temporarily inject color codes for the format string processing
        record.levelname = f"{level_color}{record.levelname}{reset}"
        record.name = f"{tag_color}[{record.name}]{reset}"
        
        # Use superclass to format the message using our temporarily modified record
        formatted_message = super().format(record)
        
        # Restore original attributes so other handlers (like the file handler) get clean text
        record.levelname = original_levelname
        record.name = original_name
        
        return formatted_message


class PlainFormatter(logging.Formatter):
    """Plain text formatter for log files (no ANSI codes)."""
    pass


# Track whether root setup has been done
_root_configured = False

# Store log directory path for lazy initialization
_log_dir: Path | None = None


def _setup_root_logger() -> None:
    """Configure the root logger with console and file handlers."""
    global _root_configured, _log_dir

    if _root_configured:
        return

    _root_configured = True

    # Get log directory from config (lazy import to avoid circular dependency)
    try:
        from assistant.core.config import config
        _log_dir = config.logs_dir
    except Exception:
        # Fallback if config isn't available yet
        _log_dir = Path("data/logs")

    _log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("jarvis")
    root.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on reimport
    if root.handlers:
        return

    # Console handler — INFO and above, colorized
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter("%(name)s %(levelname)s: %(message)s"))
    root.addHandler(console_handler)

    # File handler — DEBUG and above, rotating (5MB × 3 backups)
    try:
        log_file = _log_dir / "jarvis.log"
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            PlainFormatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )
        root.addHandler(file_handler)
    except Exception as e:
        print(f"[Logger] Warning: Could not set up file logging: {e}")


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a named logger for a specific module.

    Args:
        module_name: Short module identifier (e.g., "LLM", "Mouth", "Ear")

    Returns:
        logging.Logger: Configured logger instance
    """
    _setup_root_logger()
    return logging.getLogger(f"jarvis.{module_name}")
