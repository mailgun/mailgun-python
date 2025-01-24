"""TAGS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-tags.html
"""

from __future__ import annotations

from os import path
from typing import Any
from urllib.parse import quote


def handle_tags(
    url: Any,
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
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
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    base = url["base"] + domain + "/"
    keys_without_tags = url["keys"][1:]
    url = url["base"] + domain + final_keys
    if "tag_name" in kwargs:
        if "stats" in final_keys:
            final_keys = path.join("/", *keys_without_tags) if keys_without_tags else ""
            url = base + "tags" + "/" + quote(kwargs["tag_name"]) + final_keys
        else:
            url = url + "/" + quote(kwargs["tag_name"])

    return url
