"""MAILING LISTS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-mailinglists.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


def handle_lists(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Mailing List URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'address', 'validate', 'multiple', 'member_address').

    Returns:
        The final URL for the mailing list endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base = str(url["base"]).rstrip("/")

    if "address" not in kwargs:
        return f"{base}{final_keys}"

    safe_addr = sanitize_path_segment(kwargs["address"])

    if "validate" in kwargs:
        return f"{base}{final_keys}/{safe_addr}/validate"

    if "multiple" in kwargs and kwargs.get("multiple"):
        return f"{base}/lists/{safe_addr}/members.json"

    if "members" in final_keys:
        members_keys = build_path_from_keys(url.get("keys", [])[1:])
        if "member_address" in kwargs:
            safe_member = sanitize_path_segment(kwargs["member_address"])
            return f"{base}/lists/{safe_addr}{members_keys}/{safe_member}"
        return f"{base}/lists/{safe_addr}{members_keys}"

    return f"{base}/lists/{safe_addr}"
