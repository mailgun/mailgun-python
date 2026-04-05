"""USERS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/users
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_users(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Users URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'user_id').

    Returns:
        The final URL for the Users endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/")

    user_id = kwargs.get("user_id")

    if user_id and user_id != "me":
        return f"{base_url}/users/{user_id}"

    if user_id == "me":
        return f"{base_url}{final_keys}"

    return f"{base_url}/users"
