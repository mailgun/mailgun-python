"""Utility functions for Mailgun API handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


def build_path_from_keys(keys: Iterable[str]) -> str:
    """Join URL keys into a path segment starting with a slash.

    Args:
        keys: An iterable of string components for the URL path.

    Returns:
        A formatted path string starting with a slash, or an empty string if the iterable is empty.
    """
    keys_list = list(keys)
    return "/" + "/".join(keys_list) if keys_list else ""
