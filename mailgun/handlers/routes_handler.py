"""ROUTES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-routes.html
"""

from __future__ import annotations

from os import path
from typing import Any


def handle_routes(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Routes.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Routes endpoint
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    if "route_id" in kwargs:
        url = url["base"][:-1] + final_keys + "/" + kwargs["route_id"]
    else:
        url = url["base"][:-1] + final_keys

    return url
