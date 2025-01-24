"""EMAIL VALIDATION HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-email-validation.html#email-validation
"""

from __future__ import annotations

from os import path
from typing import Any


def handle_address_validate(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle email validation.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for email validation endpoint
    """
    final_keys = path.join("/", *url["keys"][1:]) if url["keys"][1:] else ""
    if "list_name" in kwargs:
        url = url["base"] + final_keys + "/" + kwargs["list_name"]
    else:
        url = url["base"] + final_keys

    return url
