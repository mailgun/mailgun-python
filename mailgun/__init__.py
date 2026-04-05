"""Provide a Python SDK for interacting with the Mailgun API.

This package exposes the primary client classes and custom exceptions
needed to integrate with Mailgun's services.
"""

from mailgun.client import AsyncClient
from mailgun.client import Client
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.error_handler import RouteNotFoundError
from mailgun.handlers.error_handler import UploadError


# Defines the root public API of the Mailgun SDK
__all__ = [
    "ApiError",
    "AsyncClient",
    "Client",
    "RouteNotFoundError",
    "UploadError",
]
