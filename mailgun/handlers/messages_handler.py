"""RESEND MESSAGE HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-sending.html#
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError


def handle_resend_message(
    _url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Resend message endpoint.

    Args:
        _url: Incoming URL dictionary (unused).
        _domain: Incoming domain (unused).
        _method: Incoming request method (unused).
        **kwargs: Additional keyword arguments.

    Returns:
        str: Final url for default endpoint.

    Raises:
        ApiError: If the storage_url is not provided.
    """
    if "storage_url" in kwargs:
        return str(kwargs["storage_url"])
    raise ApiError("Storage url is required")
