"""Centralized logging configuration for the Mailgun Python SDK."""

import logging

from mailgun.filters import RedactingFilter


# Singleton filter instance to avoid redundant memory allocations
_SECURITY_FILTER = RedactingFilter()


def get_logger(name: str) -> logging.Logger:
    """Create and return a pre-configured logger with security guardrails.

    Args:
        name: The module name (typically __name__).

    Returns:
        A secure logger instance protected against CWE-316.
    """
    logger = logging.getLogger(name)

    # 1. Apply the CWE-316/117 log redaction filter to ALL SDK loggers
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(_SECURITY_FILTER)

    # 2. Attach NullHandler to the root 'mailgun' namespace to prevent
    # "No handler found" warnings if the end-user hasn't configured logging.
    if name.startswith("mailgun"):
        root_logger = logging.getLogger("mailgun")
        if not root_logger.hasHandlers():
            root_logger.addHandler(logging.NullHandler())

    return logger
