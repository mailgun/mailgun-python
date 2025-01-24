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
    if "template_name" in kwargs:
        if "versions" in kwargs:
            if kwargs["versions"]:
                if "tag" in kwargs:
                    url = (
                        url["base"]
                        + domain
                        + final_keys
                        + "/"
                        + kwargs["template_name"]
                        + "/versions/"
                        + kwargs["tag"]
                    )
                else:
                    url = (
                        url["base"]
                        + domain
                        + final_keys
                        + "/"
                        + kwargs["template_name"]
                        + "/versions"
                    )
            else:
                raise ApiError("Versions should be True or absent")
        else:
            url = url["base"] + domain + final_keys + "/" + kwargs["template_name"]
    else:
        url = url["base"] + domain + final_keys

    return url
