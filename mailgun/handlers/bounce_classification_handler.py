"""BOUNCE CLASSIFICATION HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/bounce-classification
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_bounce_classification(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/")
    return f"{base_url}{final_keys}"
