"""TEMPLATES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-templates.html
"""

from __future__ import annotations

from os import path
from typing import Any

from .error_handler import ApiError


def handle_templates(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Templates.

    :param url: Incoming URL dictionary
    :type url: dict
    :param domain: Incoming domain
    :type domain: str
    :param _method: Incoming request method (but not used here)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Templates endpoint
    :raises: ApiError
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    domain_url = f"{url['base']}{domain}{final_keys}"

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
