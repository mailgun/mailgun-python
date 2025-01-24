"""DEFAULT HANDLER.

Events doc: https://documentation.mailgun.com/en/latest/api-events.html
Messages doc: https://documentation.mailgun.com/en/latest/api-sending.html
Stats doc: https://documentation.mailgun.com/en/latest/api-stats.html
"""

from __future__ import annotations

from os import path
from typing import Any

from .error_handler import ApiError


def handle_default(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **_: Any,
) -> Any:
    """Provide default handler for endpoints with single url pattern (events, messages, stats).

    :param url: Incoming URL dictionary
    :type url: dict
    :param domain: Incoming domain
    :type domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for default endpoint
    :raises: ApiError
    """
    if not domain:
        raise ApiError("Domain is missing!")

    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    return url["base"] + domain + final_keys
