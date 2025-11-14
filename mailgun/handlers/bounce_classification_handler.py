"""BOUNCE CLASSIFICATION HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/bounce-classification
"""

from __future__ import annotations

from os import path
from typing import Any


def handle_bounce_classification(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Bounce Classification.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Bounce Classification endpoints
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""

    return url["base"][:-1] + final_keys
