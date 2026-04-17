"""Utility functions for Mailgun API handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote


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
