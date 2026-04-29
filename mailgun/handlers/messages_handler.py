"""RESEND MESSAGE HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-sending.html#
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import validate_mailgun_url


def handle_resend_message(
    _url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle the resend message endpoint URL construction.

    Args:
        _url: Incoming URL configuration dictionary (unused).
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments containing the 'storage_url'.

    Returns:
        The final URL for the resend message endpoint.

    Raises:
        ApiError: If the storage_url is not provided in kwargs.
    """
    if "storage_url" not in kwargs:
        raise ApiError("Storage url is required")

    return validate_mailgun_url(str(kwargs["storage_url"]))
