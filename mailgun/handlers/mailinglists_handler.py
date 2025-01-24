"""MAILING LISTS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-mailinglists.html
"""

from __future__ import annotations

from os import path
from typing import Any


def handle_lists(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Mailing List.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for mailinglist endpoint
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    if "validate" in kwargs:
        url = url["base"][:-1] + final_keys + "/" + kwargs["address"] + "/" + "validate"
    elif "multiple" in kwargs and "address" in kwargs:
        if kwargs["multiple"]:
            url = url["base"][:-1] + "/lists/" + kwargs["address"] + "/members.json"
    elif "members" in final_keys and "address" in kwargs:
        members_keys = path.join("/", *url["keys"][1:]) if url["keys"][1:] else ""
        if "member_address" in kwargs:
            url = (
                url["base"][:-1]
                + "/lists/"
                + kwargs["address"]
                + members_keys
                + "/"
                + kwargs["member_address"]
            )
        else:
            url = url["base"][:-1] + "/lists/" + kwargs["address"] + members_keys
    elif "address" in kwargs and "validate" not in kwargs:
        url = url["base"][:-1] + final_keys + "/" + kwargs["address"]

    else:
        url = url["base"][:-1] + final_keys

    return url
