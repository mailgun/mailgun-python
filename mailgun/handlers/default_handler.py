"""DEFAULT HANDLER.

Events doc: https://documentation.mailgun.com/en/latest/api-events.html
Messages doc: https://documentation.mailgun.com/en/latest/api-sending.html
Stats doc: https://documentation.mailgun.com/en/latest/api-stats.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys


def handle_default(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **_: Any,
) -> str:
    """Provide default handler for endpoints with a single URL pattern.

    Handles resolving paths for endpoints such as events, messages, and stats.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **_: Additional keyword arguments (unused).

    Returns:
        The final resolved URL for the endpoint.

    Raises:
        ApiError: If the domain is missing.
    """
    if not domain:
        raise ApiError("Domain is missing!")

    final_keys = build_path_from_keys(url.get("keys", []))
    return f"{url['base']}{domain}{final_keys}"
