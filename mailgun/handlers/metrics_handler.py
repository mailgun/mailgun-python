"""METRICS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/openapi-final/tag/Metrics/
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_metrics(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Metrics and Tags New URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'usage', 'limits', 'tags').

    Returns:
        The final URL for the Metrics and Tags New endpoints.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base = url["base"][:-1]
    if "usage" in kwargs:
        return f"{base}/{kwargs['usage']}{final_keys}"
    if "limits" in kwargs and "tags" in kwargs:
        return f"{base}{final_keys}/{kwargs['limits']}"
    return f"{base}{final_keys}"
