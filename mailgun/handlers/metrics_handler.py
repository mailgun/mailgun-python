"""METRICS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/openapi-final/tag/Metrics/
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


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
    base = str(url["base"]).rstrip("/")

    if "usage" in kwargs:
        safe_usage = sanitize_path_segment(kwargs["usage"])
        return f"{base}/{safe_usage}{final_keys}"

    if "limits" in kwargs and "tags" in kwargs:
        safe_limits = sanitize_path_segment(kwargs["limits"])
        return f"{base}{final_keys}/{safe_limits}"

    return f"{base}{final_keys}"
