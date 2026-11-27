"""IP_POOLS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ip-pools.html
"""

from __future__ import annotations

from typing import Any

from mailgun.endpoints import build_path_from_keys
from mailgun.security import SecurityGuard


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
    url_keys = list(url.get("keys", []))
    base_prefix = str(url["base"]).rstrip("/")

    if "ips.json" in url_keys or len(url_keys) <= 1 or url_keys[0] != "ip_pools":
        final_keys = build_path_from_keys(url_keys)
        base_url = base_prefix + final_keys
        if "pool_id" not in kwargs:
            return base_url
        safe_pool = SecurityGuard.sanitize_path_segment(kwargs["pool_id"])
        pool_url = f"{base_url}/{safe_pool}"
        if "ips.json" in final_keys:
            return pool_url
        if "ip" in kwargs:
            safe_ip = SecurityGuard.sanitize_path_segment(kwargs["ip"])
            return f"{pool_url}/ips/{safe_ip}"
        return pool_url

    root_url = base_prefix + build_path_from_keys(url_keys[:1])
    sub_keys = build_path_from_keys(url_keys[1:])
    if "pool_id" not in kwargs:
        return f"{root_url}{sub_keys}"
    safe_pool = SecurityGuard.sanitize_path_segment(kwargs["pool_id"])
    pool_url = f"{root_url}/{safe_pool}{sub_keys}"
    if "ip" in kwargs:
        safe_ip = SecurityGuard.sanitize_path_segment(kwargs["ip"])
        return f"{pool_url}/{safe_ip}"
    return pool_url
