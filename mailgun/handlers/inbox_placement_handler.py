"""INBOX PLACEMENT HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-inbox-placement.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys


def handle_inbox(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle inbox placement URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Target domain name (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional parameters (e.g., 'test_id', 'counters', 'checks', 'address').

    Returns:
        The final URL for the inbox placement endpoint.

    Raises:
        ApiError: If 'counters' or 'checks' options are provided but evaluate to False.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = url["base"].rstrip("/")
    endpoint_url = f"{base_url}{final_keys}"

    if "test_id" not in kwargs:
        return endpoint_url

    test_id = kwargs["test_id"]
    endpoint_url = f"{endpoint_url}/{test_id}"

    if "counters" in kwargs:
        if kwargs["counters"]:
            return f"{endpoint_url}/counters"
        raise ApiError("Counters option should be True or absent")

    if "checks" in kwargs:
        if kwargs["checks"]:
            if "address" in kwargs:
                return f"{endpoint_url}/checks/{kwargs['address']}"
            return f"{endpoint_url}/checks"
        raise ApiError("Checks option should be True or absent")

    return endpoint_url
