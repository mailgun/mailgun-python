"""USERS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/users
"""

from __future__ import annotations

from os import path
from typing import Any


def handle_users(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Users.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for Users endpoint
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    if "org_id" in kwargs:
        url = (
            url["base"][:-1]
            + "/"
            + "users"
            + "/"
            + kwargs["user_id"]
            + "/"
            + "org"
            + "/"
            + kwargs["org_id"]
        )
    elif "user_id" in kwargs and kwargs["user_id"] != "me":
        url = url["base"][:-1] + "/" + "users" + "/" + kwargs["user_id"]
    elif "user_id" in kwargs and kwargs["user_id"] == "me":
        url = url["base"][:-1] + final_keys
    else:
        url = url["base"][:-1] + "/" + "users"

    return url
