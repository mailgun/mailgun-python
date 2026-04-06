"""DEFAULT HANDLER.

Provides a universal fallback for standard API endpoints.
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


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

    # Advanced Path Interpolation: Support modern endpoints like /v2/x509/{domain}/status
    if f"{domain}" in final_keys and domain:
        final_keys = final_keys.replace("{domain}", domain)
        domain = None  # Consume the domain so it isn't prepended later

    # Support other dynamic parameters (e.g., {subaccountId}) passed via kwargs
    for key, value in kwargs.items():
        token = f"{{{key}}}"
        if token in final_keys:
            final_keys = final_keys.replace(token, str(value))

    # Traditional prepending for standard endpoints (e.g., /v3/domain.com/messages)
    if domain:
        return f"{base_url}/{domain}{final_keys}"

    return f"{base_url}{final_keys}"
