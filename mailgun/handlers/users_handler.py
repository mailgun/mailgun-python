"""USERS HANDLER.

Doc: https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/users
"""

from __future__ import annotations

from typing import Any


def handle_users(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
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
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    base_url = str(url["base"]).rstrip("/")

    user_id = kwargs.get("user_id")

    if user_id and user_id != "me":
        return f"{base_url}/users/{user_id}"

    if user_id == "me":
        return f"{base_url}{final_keys}"

    return f"{base_url}/users"
