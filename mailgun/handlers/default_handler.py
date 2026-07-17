"""DEFAULT HANDLER.

Provides a universal fallback for standard API endpoints.
"""

from __future__ import annotations

from typing import Any

from mailgun.endpoints import build_path_from_keys
from mailgun.security import SecurityGuard


def handle_default(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Provide a universal fallback handler for endpoint URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name (optional).
        _method: Incoming request method (unused).
        **kwargs: Additional keyword arguments for template injection.

    Returns:
        The final resolved URL for the endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/")

    # Advanced Path Interpolation: Explicitly search for literal "{domain}"
    # Note: Braces are URL-encoded by build_path_from_keys to %7B and %7D
    if "%7Bdomain%7D" in final_keys and domain:
        safe_domain = SecurityGuard.sanitize_path_segment(domain)
        final_keys = final_keys.replace("%7Bdomain%7D", safe_domain)
        domain = None  # Consume the domain so it isn't prepended later

    # Support other dynamic parameters (e.g., {subaccountId}, {name}) passed via kwargs
    for key, value in kwargs.items():
        token = f"%7B{key}%7D"
        if token in final_keys:
            safe_val = SecurityGuard.sanitize_path_segment(value)
            final_keys = final_keys.replace(token, safe_val)

    # Traditional prepending for standard endpoints (e.g., /v3/domain.com/blocklists)
    if domain:
        safe_domain = SecurityGuard.sanitize_path_segment(domain)
        return f"{base_url}/{safe_domain}{final_keys}"

    return f"{base_url}{final_keys}"
