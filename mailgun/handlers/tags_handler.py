"""TAGS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-tags.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


def handle_tags(
    url: Any,
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Tags URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'tag_name').

    Returns:
        The final URL for the Tags endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url.get("base", "")).rstrip("/")

    base = f"{base_url}/{domain}/"
    keys_without_tags = url.get("keys", [])[1:]

    result_url = f"{base_url}/{domain}{final_keys}"

    if "tag_name" in kwargs:
        safe_tag = sanitize_path_segment(kwargs["tag_name"])
        if "stats" in final_keys:
            final_keys_stats = build_path_from_keys(keys_without_tags)
            return f"{base}tags/{safe_tag}{final_keys_stats}"
        return f"{result_url}/{safe_tag}"

    return result_url
