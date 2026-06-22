"""Provide a Python SDK for interacting with the Mailgun API.

This package exposes the primary client classes, fluent builders, and
custom exceptions needed to securely integrate with Mailgun's services.
"""

from __future__ import annotations

from mailgun._version import __version__
from mailgun.builders import MailgunMessageBuilder, MailgunTemplateBuilder
from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import (
    ApiError,
    MailgunTimeoutError,
    RouteNotFoundError,
    UploadError,
)


# Defines the root public API of the Mailgun SDK
__all__ = [
    "ApiError",
    "AsyncClient",
    "Client",
    "MailgunMessageBuilder",
    "MailgunTemplateBuilder",
    "MailgunTimeoutError",
    "RouteNotFoundError",
    "UploadError",
    "__version__",
]
