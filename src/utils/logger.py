"""Logging setup for console and rotating file output."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from src.constants import CONFIG_DIR, LOG_DATE_FORMAT, LOG_DIR, LOG_FILE, LOG_FORMAT


def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Create the application logger with console and file handlers.

    Logs are written to ``~/.pdfmaster/logs/pdfmaster.log`` and echoed
    to stderr. The config directory is created if it does not exist.

    Args:
        level: Logging level name or constant (default INFO).
        log_file: Optional override for the log file path.

    Returns:
        The configured root application logger (``pdfmaster``).
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    target = Path(log_file) if log_file else LOG_FILE

    logger = logging.getLogger("pdfmaster")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        target,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.debug("Logging initialized at %s (file=%s)", logging.getLevelName(level), target)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``pdfmaster`` namespace.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        A logger instance that inherits handlers from ``pdfmaster``.
    """
    if name.startswith("pdfmaster"):
        return logging.getLogger(name)
    return logging.getLogger(f"pdfmaster.{name}")
