"""SUPPRESSION HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-suppressions.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url.get("base", "")).rstrip("/")
    base = f"{base_url}/{domain}{final_keys}"

    if "bounce_address" in kwargs:
        safe_addr = sanitize_path_segment(kwargs["bounce_address"])
        return f"{base}/{safe_addr}"
    return base


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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url.get("base", "")).rstrip("/")
    base = f"{base_url}/{domain}{final_keys}"

    if "unsubscribe_address" in kwargs:
        safe_addr = sanitize_path_segment(kwargs["unsubscribe_address"])
        return f"{base}/{safe_addr}"
    return base


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
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url.get("base", "")).rstrip("/")
    base = f"{base_url}/{domain}{final_keys}"

    if "complaint_address" in kwargs:
        safe_addr = sanitize_path_segment(kwargs["complaint_address"])
        return f"{base}/{safe_addr}"
    return base


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
    base_url = str(url.get("base", "")).rstrip("/")
    base = f"{base_url}/{domain}{final_keys}"

    if "whitelist_address" in kwargs:
        safe_addr = sanitize_path_segment(kwargs["whitelist_address"])
        return f"{base}/{safe_addr}"
    return base
