"""TEMPLATES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-templates.html
"""

from __future__ import annotations

from typing import Any

from .error_handler import ApiError


def handle_templates(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Templates dynamically resolving V3 (Domain) or V4 (Account).

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
    # Safe path building without relying on os.path.join (which uses '\\' on Windows)
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""

    base_url_str = url["base"]

    # DYNAMIC VERSION OVERRIDE:
    # Mailgun splits Templates API across two versions depending on the scope.
    if domain:
        # Domain Templates ALWAYS use V3: /v3/{domain_name}/templates
        if "/v4/" in base_url_str:
            base_url_str = base_url_str.replace("/v4/", "/v3/")
        domain_url = f"{base_url_str}{domain}{final_keys}"
    else:
        # Account Templates ALWAYS use V4: /v4/templates
        if "/v3/" in base_url_str:
            base_url_str = base_url_str.replace("/v3/", "/v4/")
        domain_url = f"{base_url_str}{final_keys.lstrip('/')}"

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
