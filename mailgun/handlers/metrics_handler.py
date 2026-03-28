"""METRICS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/openapi-final/tag/Metrics/
"""

from __future__ import annotations

from typing import Any


def handle_metrics(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Metrics and Tags New.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Metrics and Tags New endpoints
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    base = url["base"][:-1]
    if "usage" in kwargs:
        return f"{base}/{kwargs['usage']}{final_keys}"
    elif "limits" in kwargs and "tags" in kwargs:
        return f"{base}/{final_keys}{kwargs['limits']}"
    return f"{base}{final_keys}"
