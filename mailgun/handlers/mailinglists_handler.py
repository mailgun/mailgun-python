"""MAILING LISTS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-mailinglists.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


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
    base = url["base"][:-1]
    if "validate" in kwargs:
        return f"{base}{final_keys}/{kwargs['address']}/validate"
    if "multiple" in kwargs and "address" in kwargs:
        if kwargs["multiple"]:
            return f"{base}/lists/{kwargs['address']}/members.json"
    elif "members" in final_keys and "address" in kwargs:
        members_keys = "/" + "/".join(url["keys"][1:]) if url["keys"][1:] else ""
        if "member_address" in kwargs:
            return f"{base}/lists/{kwargs['address']}{members_keys}/{kwargs['member_address']}"
        return f"{base}/lists/{kwargs['address']}{members_keys}"
    elif "address" in kwargs:
        return f"{base}/lists/{kwargs['address']}"

    return f"{base}{final_keys}"
