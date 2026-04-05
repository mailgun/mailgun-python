"""BOUNCE CLASSIFICATION HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/bounce-classification
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_bounce_classification(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **_kwargs: Any,
) -> str:
    """Handle Bounce Classification URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **_kwargs: Additional keyword arguments (unused).

    Returns:
        The final URL for the Bounce Classification endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/")
    return f"{base_url}{final_keys}"
