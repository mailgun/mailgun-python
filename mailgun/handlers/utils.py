"""Utility functions for Mailgun API handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlparse


if TYPE_CHECKING:
    from collections.abc import Iterable


def build_path_from_keys(keys: Iterable[str]) -> str:
    """Join URL keys into a path segment starting with a slash.

    Args:
        keys: An iterable of string components for the URL path.

    Returns:
        A formatted path string starting with a slash, or an empty string if the iterable is empty.
    """
    if not keys:
        return ""
    # Fast path for tuples/lists, fallback to list() for generators
    keys_seq = keys if isinstance(keys, (list, tuple)) else list(keys)
    return "/" + "/".join(keys_seq)


def sanitize_path_segment(segment: Any) -> str:
    """Poka-yoke: URL-encode path segments to prevent Path Traversal (CWE-22).

    Returns:
        The URL-encoded path segment string.
    """
    if segment is None:
        return ""
    # safe="@+" ensures email addresses pass through naturally without breaking API contracts,
    # while still strictly percent-encoding slashes (/) to block Path Traversal.
    return quote(str(segment), safe="@+")


def validate_mailgun_url(url: str) -> str:
    """Poka-yoke: Protection against SSRF and API key leakage (CWE-918).

    Checks whether the specified URL belongs to the trusted Mailgun infrastructure.
    This is critical for endpoints that accept absolute URLs (e.g. storage_url).

    Returns:
        The original URL if it passes the security check.

    Raises:
        ValueError: If the URL's hostname is untrusted or attempts to bypass security.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    allowed_suffixes = (".mailgun.net", ".mailgun.org", ".mailgun.com")
    allowed_exact = {"mailgun.net", "mailgun.org", "mailgun.com", "localhost", "127.0.0.1"}

    is_safe = hostname in allowed_exact or any(
        hostname.endswith(suffix) for suffix in allowed_suffixes
    )

    if not is_safe:
        msg = (
            f"Security Alert (CWE-918): Untrusted domain '{hostname}'. "
            "To prevent the leakage of the API-key requests are allowed to the Mailgun infrastructure only."
        )
        raise ValueError(msg)

    return url
