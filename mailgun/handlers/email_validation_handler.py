"""EMAIL VALIDATION HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-email-validation.html#email-validation
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import sanitize_path_segment


def handle_address_validate(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle email validation URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Target domain name (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional parameters, such as 'list_name'.

    Returns:
        The final URL for the email validation endpoint.
    """
    final_keys = "/" + "/".join(url["keys"][1:]) if url["keys"][1:] else ""
    base_url = str(url["base"]).rstrip("/")

    if "list_name" in kwargs:
        safe_list = sanitize_path_segment(kwargs["list_name"])
        return f"{base_url}{final_keys}/{safe_list}"
    return f"{base_url}{final_keys}"
