"""TEMPLATES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-templates.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


def handle_templates(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Templates dynamically resolving V3 (Domain) or V4 (Account).

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'template_name', 'versions', 'tag').

    Returns:
        The final URL for the Templates endpoint.

    Raises:
        ApiError: If the versions option is invalid.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url_str = str(url["base"])

    if domain:
        if "/v4/" in base_url_str:
            base_url_str = base_url_str.replace("/v4/", "/v3/")

        base_url_str = base_url_str if base_url_str.endswith("/") else f"{base_url_str}/"
        domain_url = f"{base_url_str}{domain}{final_keys}"
    else:
        if "/v3/" in base_url_str:
            base_url_str = base_url_str.replace("/v3/", "/v4/")

        base_url_str = base_url_str.rstrip("/")
        domain_url = f"{base_url_str}{final_keys}"

    if "template_name" not in kwargs:
        return domain_url

    safe_template = sanitize_path_segment(kwargs["template_name"])
    template_url = f"{domain_url}/{safe_template}"

    if "versions" not in kwargs:
        return template_url

    if not kwargs["versions"]:
        raise ApiError("Versions should be True or absent")

    versions_url = f"{template_url}/versions"

    if kwargs.get("tag"):
        safe_tag = sanitize_path_segment(kwargs["tag"])

        # Logic for template version copying
        if kwargs.get("copy") and "new_tag" in kwargs:
            safe_new_tag = sanitize_path_segment(kwargs["new_tag"])
            return f"{versions_url}/{safe_tag}/copy/{safe_new_tag}"

        return f"{versions_url}/{safe_tag}"

    return versions_url
