"""INBOX PLACEMENT HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-inbox-placement.html
"""

from __future__ import annotations

from os import path
from typing import Any

from .error_handler import ApiError


def handle_inbox(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle inbox placement.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for inbox placement endpoint
    :raises: ApiError
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    if "test_id" in kwargs:
        if "counters" in kwargs:
            if kwargs["counters"]:
                url = (
                    url["base"][:-1]
                    + final_keys
                    + "/"
                    + kwargs["test_id"]
                    + "/counters"
                )
            else:
                raise ApiError("Counters option should be True or absent")
        elif "checks" in kwargs:
            if kwargs["checks"]:
                if "address" in kwargs:
                    url = (
                        url["base"][:-1]
                        + final_keys
                        + "/"
                        + kwargs["test_id"]
                        + "/checks/"
                        + kwargs["address"]
                    )
                else:
                    url = (
                        url["base"][:-1]
                        + final_keys
                        + "/"
                        + kwargs["test_id"]
                        + "/checks"
                    )
            else:
                raise ApiError("Checks option should be True or absent")
        else:
            url = url["base"][:-1] + final_keys + "/" + kwargs["test_id"]
    else:
        url = url["base"][:-1] + final_keys

    return url
