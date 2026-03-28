"""IPS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ips.html
"""

from __future__ import annotations

from typing import Any


def handle_ips(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle IPs.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for IPs endpoint
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    base_url = url["base"][:-1] + final_keys
    if "ip" in kwargs:
        return f"{base_url}/{kwargs['ip']}"
    return base_url
