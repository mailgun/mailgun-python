"""KEYS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/keys
"""

from __future__ import annotations

from typing import Any


def handle_keys(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Keys.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Keys endpoint
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    base_url = url["base"][:-1] + final_keys
    if "key_id" in kwargs:
        return f"{base_url}/{kwargs['key_id']}"
    return base_url
