"""TEMPLATES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-templates.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys


def handle_templates(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Templates dynamically resolving V3 (Domain) or V4 (Account).

    Args:
        url: Incoming URL dictionary.
        domain: Incoming domain.
        _method: Incoming request method (unused).
        **kwargs: Additional keyword arguments.

    Returns:
        str: Final url for Templates endpoint.

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

    template_url = domain_url + f"/{kwargs['template_name']}"

    if "versions" not in kwargs:
        return template_url

    if not kwargs["versions"]:
        raise ApiError("Versions should be True or absent")

    versions_url = template_url + "/versions"

    if "tag" in kwargs and "copy" not in kwargs:
        return versions_url + f"/{kwargs['tag']}"
    if "tag" in kwargs and "copy" in kwargs and "new_tag" in kwargs:
        return versions_url + f"/{kwargs['tag']}/copy/{kwargs['new_tag']}"

    return versions_url
