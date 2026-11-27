"""IPS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ips.html
"""

from __future__ import annotations

from typing import Any

from mailgun.endpoints import build_path_from_keys
from mailgun.security import SecurityGuard


def handle_ips(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle IPs URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Target domain name (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional parameters (e.g., 'ip').

    Returns:
        The final URL for the IPs endpoint.
    """
    url_keys = list(url.get("keys", []))
    base_prefix = str(url["base"]).rstrip("/")
    if "ip" in kwargs:
        safe_ip = SecurityGuard.sanitize_path_segment(kwargs["ip"])
        if len(url_keys) > 1 and url_keys[0] == "ips":
            root_url = base_prefix + build_path_from_keys(url_keys[:1])
            sub_keys = build_path_from_keys(url_keys[1:])
            return f"{root_url}/{safe_ip}{sub_keys}"
        return f"{base_prefix}{build_path_from_keys(url_keys)}/{safe_ip}"
    return f"{base_prefix}{build_path_from_keys(url_keys)}"
