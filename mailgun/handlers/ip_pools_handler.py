"""IP_POOLS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ip-pools.html
"""

from __future__ import annotations
from os import path
from typing import Any

def handle_ippools(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle IP pools URL construction.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param kwargs: kwargs
    :return: final url for IP pools endpoint
    """
    final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
    base_url = url["base"][:-1] + final_keys

    if "pool_id" not in kwargs:
        return base_url

    pool_url = f"{base_url}/{kwargs['pool_id']}"

    if "ips.json" in final_keys:
        return pool_url

    if "ip" in kwargs:
        return f"{pool_url}/ips/{kwargs['ip']}"

    return pool_url
