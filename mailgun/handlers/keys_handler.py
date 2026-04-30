"""KEYS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/keys
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


def handle_keys(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Keys URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'key_id').

    Returns:
        The final URL for the Keys endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/") + final_keys
    if "key_id" in kwargs:
        safe_key = sanitize_path_segment(kwargs["key_id"])
        return f"{base_url}/{safe_key}"
    return base_url
