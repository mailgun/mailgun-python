"""IPS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-ips.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = url["base"][:-1] + final_keys
    if "ip" in kwargs:
        return f"{base_url}/{kwargs['ip']}"
    return base_url
