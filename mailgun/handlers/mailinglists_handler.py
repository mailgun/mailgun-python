"""MAILING LISTS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-mailinglists.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_lists(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
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
    final_keys = build_path_from_keys(url.get("keys", []))
    base = url["base"][:-1]
    if "validate" in kwargs:
        return f"{base}{final_keys}/{kwargs['address']}/validate"
    elif "multiple" in kwargs and "address" in kwargs:
        if kwargs["multiple"]:
            return f"{base}/lists/{kwargs['address']}/members.json"
    elif "members" in final_keys and "address" in kwargs:
        members_keys = "/" + "/".join(url["keys"][1:]) if url["keys"][1:] else ""
        if "member_address" in kwargs:
            return f"{base}/lists/{kwargs['address']}{members_keys}/{kwargs['member_address']}"
        return f"{base}/lists/{kwargs['address']}{members_keys}"
    elif "address" in kwargs and "validate" not in kwargs:
        return f"{base}{final_keys}/{kwargs['address']}"
    return f"{base}{final_keys}"
