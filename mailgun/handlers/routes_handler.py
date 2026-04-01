"""ROUTES HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-routes.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_routes(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = url["base"][:-1] + final_keys
    if "route_id" in kwargs:
        return f"{base_url}/{kwargs['route_id']}"
    return base_url
