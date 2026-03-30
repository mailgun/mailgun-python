"""TAGS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-tags.html
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from mailgun.handlers.utils import build_path_from_keys


def handle_tags(
    url: Any,
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Tags.

    :param url: Incoming URL dictionary
    :type url: dict
    :param domain: Incoming domain
    :type domain: str
    :param _method: Incoming request method (but not used here)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Tags endpoint
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base = url["base"] + str(domain) + "/"
    keys_without_tags = url["keys"][1:]

    result_url = url["base"] + str(domain) + final_keys

    if "tag_name" in kwargs:
        if "stats" in final_keys:
            final_keys_stats = "/" + "/".join(keys_without_tags) if keys_without_tags else ""
            return f"{base}tags/{quote(kwargs['tag_name'])}{final_keys_stats}"
        else:
            return f"{result_url}/{quote(kwargs['tag_name'])}"

    return result_url
