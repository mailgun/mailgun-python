"""IP_POOLS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ip-pools.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_ippools(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle IP pools URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Target domain name (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional parameters (e.g., 'pool_id', 'ip').

    Returns:
        The final URL for the IP pools endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/") + final_keys

    if "pool_id" not in kwargs:
        return base_url

    pool_url = f"{base_url}/{kwargs['pool_id']}"

    if "ips.json" in final_keys:
        return pool_url

    if "ip" in kwargs:
        return f"{pool_url}/ips/{kwargs['ip']}"

    return pool_url
