"""SUPPRESSION HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-suppressions.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys


def handle_bounces(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Bounces URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'bounce_address').

    Returns:
        The final URL for the Bounces endpoint.
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    if "bounce_address" in kwargs:
        url = url["base"] + str(domain) + final_keys + "/" + kwargs["bounce_address"]
    else:
        url = url["base"] + str(domain) + final_keys
    return url


def handle_unsubscribes(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Unsubscribes URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'unsubscribe_address').

    Returns:
        The final URL for the Unsubscribes endpoint.
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    if "unsubscribe_address" in kwargs:
        url = url["base"] + str(domain) + final_keys + "/" + kwargs["unsubscribe_address"]
    else:
        url = url["base"] + str(domain) + final_keys
    return url


def handle_complaints(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Complaints URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'complaint_address').

    Returns:
        The final URL for the Complaints endpoint.
    """
    final_keys = "/" + "/".join(url["keys"]) if url["keys"] else ""
    if "complaint_address" in kwargs:
        url = url["base"] + str(domain) + final_keys + "/" + kwargs["complaint_address"]
    else:
        url = url["base"] + str(domain) + final_keys
    return url


def handle_whitelists(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Whitelists URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'whitelist_address').

    Returns:
        The final URL for the Whitelists endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    if "whitelist_address" in kwargs:
        url = url["base"] + str(domain) + final_keys + "/" + kwargs["whitelist_address"]
    else:
        url = url["base"] + str(domain) + final_keys
    return str(url)
